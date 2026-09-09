// [custom] "Máy 1" — a 3-output (relay) controller on a second ESP32-S3.
//
// It joins Wi-Fi, connects to the MQTT broker on the VPS, and:
//   * turns 3 outputs on/off on command  (topic may1/cmd)
//   * keeps an optional daily on/off SCHEDULE per output and enforces it
//   * tracks how long each output has been in its current state
//   * publishes all of that back (retained) on topic may1/status
//
// The xiaozhi server (robot_bridge.py) is the only thing that talks to it, and
// the voice assistant drives the server. Commands (JSON on may1/cmd):
//   {"cmd":"set","out":1,"on":true}
//   {"cmd":"set_all","on":false}
//   {"cmd":"schedule","out":1,"on":"18:00","off":"22:00"}
//   {"cmd":"clear_schedule","out":1}
//   {"cmd":"report"}
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <sys/time.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_sntp.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "mqtt_client.h"
#include "cJSON.h"

#include "may1_config.h"
#include "may1_secrets.h"

static const char *TAG = "may1";

#define NOUT 3
static const int OUT_GPIO[NOUT] = {OUT1_GPIO, OUT2_GPIO, OUT3_GPIO};

typedef struct {
    bool on;
    time_t last_change;   // when the state last flipped (for elapsed time)
    int on_min;           // scheduled turn-ON minute of day (0..1439), -1 = none
    int off_min;          // scheduled turn-OFF minute of day, -1 = none
} output_t;

static output_t g_out[NOUT];
static SemaphoreHandle_t g_lock;
static esp_mqtt_client_handle_t g_mqtt;
static bool g_mqtt_up = false;

static EventGroupHandle_t g_wifi_eg;
#define WIFI_CONNECTED_BIT BIT0

// ---- output control ----
static int relay_level(bool on) { return RELAY_ACTIVE_HIGH ? (on ? 1 : 0) : (on ? 0 : 1); }

static void apply_output(int i, bool on) {
    if (i < 0 || i >= NOUT) return;
    if (g_out[i].on != on) {
        g_out[i].on = on;
        g_out[i].last_change = time(NULL);
    }
    gpio_set_level(OUT_GPIO[i], relay_level(on));
}

// ---- helpers ----
static int hhmm_to_min(const char *s) {
    if (!s) return -1;
    int h = 0, m = 0;
    if (sscanf(s, "%d:%d", &h, &m) != 2) return -1;
    if (h < 0 || h > 23 || m < 0 || m > 59) return -1;
    return h * 60 + m;
}
static void min_to_hhmm(int mn, char *buf, size_t n) {
    if (mn < 0) { if (n) buf[0] = '\0'; return; }
    snprintf(buf, n, "%02d:%02d", mn / 60, mn % 60);
}

// ---- publish retained status ----
static void publish_status(void) {
    if (!g_mqtt || !g_mqtt_up) return;
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "ts", (double)time(NULL));
    cJSON *arr = cJSON_AddArrayToObject(root, "outs");
    xSemaphoreTake(g_lock, portMAX_DELAY);
    time_t now = time(NULL);
    for (int i = 0; i < NOUT; i++) {
        cJSON *o = cJSON_CreateObject();
        cJSON_AddBoolToObject(o, "on", g_out[i].on);
        long since = g_out[i].last_change ? (long)(now - g_out[i].last_change) : 0;
        if (since < 0) since = 0;
        cJSON_AddNumberToObject(o, "since_s", since);
        char b[8];
        min_to_hhmm(g_out[i].on_min, b, sizeof(b));  cJSON_AddStringToObject(o, "on_time", b);
        min_to_hhmm(g_out[i].off_min, b, sizeof(b)); cJSON_AddStringToObject(o, "off_time", b);
        cJSON_AddItemToArray(arr, o);
    }
    xSemaphoreGive(g_lock);
    char *s = cJSON_PrintUnformatted(root);
    if (s) {
        esp_mqtt_client_publish(g_mqtt, TOPIC_STATUS, s, 0, 1, 1 /* retain */);
        cJSON_free(s);
    }
    cJSON_Delete(root);
}

// ---- handle a command JSON ----
static void handle_cmd(const char *data, int len) {
    cJSON *root = cJSON_ParseWithLength(data, len);
    if (!root) { ESP_LOGW(TAG, "bad cmd json"); return; }
    const cJSON *jc = cJSON_GetObjectItem(root, "cmd");
    const char *cmd = cJSON_IsString(jc) ? jc->valuestring : "";

    xSemaphoreTake(g_lock, portMAX_DELAY);
    if (strcmp(cmd, "set") == 0) {
        int out = cJSON_GetObjectItem(root, "out") ? cJSON_GetObjectItem(root, "out")->valueint : 0;
        bool on = cJSON_IsTrue(cJSON_GetObjectItem(root, "on"));
        if (out >= 1 && out <= NOUT) apply_output(out - 1, on);
    } else if (strcmp(cmd, "set_all") == 0) {
        bool on = cJSON_IsTrue(cJSON_GetObjectItem(root, "on"));
        for (int i = 0; i < NOUT; i++) apply_output(i, on);
    } else if (strcmp(cmd, "schedule") == 0) {
        int out = cJSON_GetObjectItem(root, "out") ? cJSON_GetObjectItem(root, "out")->valueint : 0;
        const cJSON *jon = cJSON_GetObjectItem(root, "on");
        const cJSON *joff = cJSON_GetObjectItem(root, "off");
        if (out >= 1 && out <= NOUT) {
            if (cJSON_IsString(jon))  g_out[out - 1].on_min  = hhmm_to_min(jon->valuestring);
            if (cJSON_IsString(joff)) g_out[out - 1].off_min = hhmm_to_min(joff->valuestring);
        }
    } else if (strcmp(cmd, "clear_schedule") == 0) {
        int out = cJSON_GetObjectItem(root, "out") ? cJSON_GetObjectItem(root, "out")->valueint : 0;
        if (out >= 1 && out <= NOUT) { g_out[out - 1].on_min = -1; g_out[out - 1].off_min = -1; }
    }
    xSemaphoreGive(g_lock);
    cJSON_Delete(root);
    publish_status();
}

// ---- MQTT ----
static void mqtt_event_handler(void *args, esp_event_base_t base, int32_t id, void *data) {
    esp_mqtt_event_handle_t e = data;
    switch ((esp_mqtt_event_id_t)id) {
    case MQTT_EVENT_CONNECTED:
        g_mqtt_up = true;
        ESP_LOGI(TAG, "MQTT connected");
        esp_mqtt_client_publish(g_mqtt, TOPIC_ONLINE, "1", 0, 1, 1);
        esp_mqtt_client_subscribe(g_mqtt, TOPIC_CMD, 1);
        publish_status();
        break;
    case MQTT_EVENT_DISCONNECTED:
        g_mqtt_up = false;
        ESP_LOGW(TAG, "MQTT disconnected");
        break;
    case MQTT_EVENT_DATA:
        if (e->topic_len && strncmp(e->topic, TOPIC_CMD, e->topic_len) == 0) {
            handle_cmd(e->data, e->data_len);
        }
        break;
    default:
        break;
    }
}

static void mqtt_start(void) {
    esp_mqtt_client_config_t cfg = {
        .broker.address.hostname = MQTT_HOST,
        .broker.address.port = MQTT_PORT,
        .broker.address.transport = MQTT_TRANSPORT_OVER_TCP,
        .credentials.username = MQTT_USERNAME,
        .credentials.authentication.password = MQTT_PASSWORD,
        .session.last_will.topic = TOPIC_ONLINE,
        .session.last_will.msg = "0",
        .session.last_will.msg_len = 1,
        .session.last_will.qos = 1,
        .session.last_will.retain = 1,
        .session.keepalive = 30,
    };
    g_mqtt = esp_mqtt_client_init(&cfg);
    esp_mqtt_client_register_event(g_mqtt, ESP_EVENT_ANY_ID, mqtt_event_handler, NULL);
    esp_mqtt_client_start(g_mqtt);
}

// ---- schedule + status task ----
static void worker_task(void *arg) {
    int last_min = -1;
    int tick = 0;
    while (1) {
        time_t now = time(NULL);
        struct tm tm;
        localtime_r(&now, &tm);
        int now_min = tm.tm_hour * 60 + tm.tm_min;
        // enforce the schedule once per minute
        if (now_min != last_min) {
            last_min = now_min;
            xSemaphoreTake(g_lock, portMAX_DELAY);
            for (int i = 0; i < NOUT; i++) {
                if (g_out[i].on_min == now_min && !g_out[i].on) apply_output(i, true);
                if (g_out[i].off_min == now_min && g_out[i].on) apply_output(i, false);
            }
            xSemaphoreGive(g_lock);
        }
        if (++tick >= STATUS_PERIOD_S / 2) { tick = 0; publish_status(); }
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}

// ---- Wi-Fi ----
static void wifi_event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupClearBits(g_wifi_eg, WIFI_CONNECTED_BIT);
        ESP_LOGW(TAG, "Wi-Fi disconnected, retrying");
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ESP_LOGI(TAG, "Wi-Fi got IP");
        xEventGroupSetBits(g_wifi_eg, WIFI_CONNECTED_BIT);
    }
}

static void wifi_start(void) {
    g_wifi_eg = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t ic = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&ic));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event_handler, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event_handler, NULL, NULL));
    wifi_config_t wc = { 0 };
    strncpy((char *)wc.sta.ssid, WIFI_SSID, sizeof(wc.sta.ssid) - 1);
    strncpy((char *)wc.sta.password, WIFI_PASSWORD, sizeof(wc.sta.password) - 1);
    wc.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wc));
    ESP_ERROR_CHECK(esp_wifi_start());
}

static void time_sync_start(void) {
    setenv("TZ", DEVICE_TZ, 1);
    tzset();
    esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, "pool.ntp.org");
    esp_sntp_setservername(1, "time.google.com");
    esp_sntp_init();
}

void app_main(void) {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    g_lock = xSemaphoreCreateMutex();
    for (int i = 0; i < NOUT; i++) {
        g_out[i].on = false;
        g_out[i].last_change = 0;
        g_out[i].on_min = -1;
        g_out[i].off_min = -1;
        gpio_config_t gc = {
            .pin_bit_mask = 1ULL << OUT_GPIO[i],
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&gc);
        gpio_set_level(OUT_GPIO[i], relay_level(false)); // start OFF
    }

    wifi_start();
    xEventGroupWaitBits(g_wifi_eg, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
    time_sync_start();
    mqtt_start();
    xTaskCreate(worker_task, "may1_worker", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "may1 controller started");
}
