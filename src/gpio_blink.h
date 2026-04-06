#ifndef GPIO_BLINK_H
#define GPIO_BLINK_H

/**
 * gpio_blink.h
 * GPIO control interface for the Blink reactor on Raspberry Pi 5.
 * Uses the lgpio library (RPi5 RP1 chip → gpiochip4).
 */

int  gpio_blink_init(int pin);
void gpio_blink_set_high(int pin);
void gpio_blink_set_low(int pin);
void gpio_blink_cleanup(int pin);

#endif /* GPIO_BLINK_H */
