#ifndef _BOARD_CONFIG_H_
#define _BOARD_CONFIG_H_

#include <driver/gpio.h>

// =============================================================================
//  DIYMORE ESP32-S3 2.8" Capacitive Touch LCD board
//  - MCU:     ESP32-S3 (N16R8: 16MB flash, 8MB Octal PSRAM)
//  - LCD:     2.8" IPS 240x320, driver ILI9341V, 4-line SPI
//  - Touch:   FT6336G capacitive, I2C (addr 0x38), INT=GPIO17, RST=GPIO18
//  - Audio:   ES8311 codec (built-in mic + speaker port)
//  - Extras:  MicroSD (own SPI), RGB LED, battery port (ADC on GPIO9)
//
//  Pin map VERIFIED against the LCDwiki ES3C28P Board Support Package:
//  https://github.com/ngttai/esp32_s3_es3c28p (include/bsp/esp32_s3_es3c28p.h)
//  LCD + audio + I2C pins are identical to the freenove-esp32s3-display-2.8-lcd
//  board in xiaozhi, so that target is display-compatible with this hardware.
// =============================================================================

#define AUDIO_INPUT_SAMPLE_RATE  24000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000

// ---- Audio I2S (to ES8311 codec) ----
#define AUDIO_I2S_GPIO_MCLK      GPIO_NUM_4   // MCLK
#define AUDIO_I2S_GPIO_BCLK      GPIO_NUM_5   // SCK / BCLK
#define AUDIO_I2S_GPIO_DIN       GPIO_NUM_6   // DIN  (mic -> ESP32)  [BSP DSIN]
#define AUDIO_I2S_GPIO_WS        GPIO_NUM_7   // LRC / WS             [BSP LCLK]
#define AUDIO_I2S_GPIO_DOUT      GPIO_NUM_8   // DOUT (ESP32 -> speaker)
#define AUDIO_CODEC_PA_PIN       GPIO_NUM_1   // Power-amp enable     [BSP POWER_AMP_IO]

// ---- Audio codec I2C (shared with touch) ----
#define AUDIO_CODEC_I2C_NUM      I2C_NUM_0
#define AUDIO_CODEC_I2C_SCL_PIN  GPIO_NUM_15
#define AUDIO_CODEC_I2C_SDA_PIN  GPIO_NUM_16
#define AUDIO_CODEC_ES8311_ADDR  ES8311_CODEC_DEFAULT_ADDR

// ---- Touch FT6336 (I2C 15/16, addr 0x38) ----
#define TOUCH_INT_PIN            GPIO_NUM_17
#define TOUCH_RST_PIN            GPIO_NUM_18

// ---- Buttons / LED ----
#define BOOT_BUTTON_GPIO         GPIO_NUM_0
#define BUILTIN_LED_GPIO         GPIO_NUM_42

// ---- Display (ILI9341, SPI3) ----
#define DISPLAY_BACKLIGHT_PIN    GPIO_NUM_45  // high = backlight ON
#define DISPLAY_RST_PIN          GPIO_NUM_NC  // shares ESP32-S3 reset
#define DISPLAY_SCK_PIN          GPIO_NUM_12  // PCLK
#define DISPLAY_DC_PIN           GPIO_NUM_46
#define DISPLAY_CS_PIN           GPIO_NUM_10
#define DISPLAY_MOSI_PIN         GPIO_NUM_11
#define DISPLAY_MIS0_PIN         GPIO_NUM_13
#define DISPLAY_SPI_SCLK_HZ      (40 * 1000 * 1000)  // BSP uses 40MHz

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
