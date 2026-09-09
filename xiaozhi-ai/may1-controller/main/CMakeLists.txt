idf_component_register(
    SRCS "may1_main.c"
    INCLUDE_DIRS "."
    REQUIRES esp_wifi esp_netif esp_event nvs_flash driver mqtt json lwip esp_timer
)
