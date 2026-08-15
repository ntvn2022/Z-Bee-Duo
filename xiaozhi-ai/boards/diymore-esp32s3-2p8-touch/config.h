#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_

#include <driver/gpio.h>

// =============================================================================
//  DIYMORE ESP32-S3 2.8" Capacitive Touch LCD board
//  - MCU:     ESP32-S3
//  - LCD:     2.8" IPS 240x320, driver ILI9341V, 4-line SPI
//  - Touch:   FT6336G capacitive, I2C (addr 0x38)
//  - Audio:   ES8311 codec (built-in mic + speaker port)  <-- verify on your unit
//  - Extras:  MicroSD, RGB LED, battery port
//
//  This config is based on the Freenove / LCDwiki ES3C28P design, which uses the
//  same reference hardware. If audio or the screen does not work, verify the pins
//  below against your board's silkscreen / schematic and adjust.
// =============================================================================

#define AUDIO_INPUT_SAMPLE_RATE  24000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000

// ---- Audio I2S (to ES8311 codec) ----  VERIFY on your board
#define AUDIO_I2S_GPIO_MCLK      GPIO_NUM_4   // MCLK
#define AUDIO_I2S_GPIO_BCLK      GPIO_NUM_5   // SCK / BCLK
#define AUDIO_I2S_GPIO_DIN       GPIO_NUM_6   // DIN  (mic -> ESP32)
#define AUDIO_I2S_GPIO_WS        GPIO_NUM_7   // LRC / WS
#define AUDIO_I2S_GPIO_DOUT      GPIO_NUM_8   // DOUT (ESP32 -> speaker)
#define AUDIO_CODEC_PA_PIN       GPIO_NUM_1   // Power-amp enable

// ---- Audio codec I2C ----  VERIFY on your board
#define AUDIO_CODEC_I2C_NUM      I2C_NUM_0
#define AUDIO_CODEC_I2C_SCL_PIN  GPIO_NUM_15
#define AUDIO_CODEC_I2C_SDA_PIN  GPIO_NUM_16
#define AUDIO_CODEC_ES8311_ADDR  ES8311_CODEC_DEFAULT_ADDR

// ---- Buttons / LED ----
#define BOOT_BUTTON_GPIO         GPIO_NUM_0
#define BUILTIN_LED_GPIO         GPIO_NUM_42

// ---- Display (ILI9341, SPI) ----
#define DISPLAY_BACKLIGHT_PIN    GPIO_NUM_45
#define DISPLAY_RST_PIN          GPIO_NUM_NC
#define DISPLAY_SCK_PIN          GPIO_NUM_12
#define DISPLAY_DC_PIN           GPIO_NUM_46
#define DISPLAY_CS_PIN           GPIO_NUM_10
#define DISPLAY_MOSI_PIN         GPIO_NUM_11
#define DISPLAY_MIS0_PIN         GPIO_NUM_13
#define DISPLAY_SPI_SCLK_HZ      (20 * 1000 * 1000)

#define LCD_SPI_HOST             SPI3_HOST

#define LCD_TYPE_ILI9341_SERIAL
#define DISPLAY_WIDTH            320
#define DISPLAY_HEIGHT           240
#define DISPLAY_MIRROR_X         false
#define DISPLAY_MIRROR_Y         false
#define DISPLAY_SWAP_XY          true
#define DISPLAY_INVERT_COLOR     true
#define DISPLAY_RGB_ORDER        LCD_RGB_ELEMENT_ORDER_BGR
#define DISPLAY_OFFSET_X         0
#define DISPLAY_OFFSET_Y         0
#define DISPLAY_BACKLIGHT_OUTPUT_INVERT false
#define DISPLAY_SPI_MODE         0

#endif  // _BOARD_CONFIG_H_
