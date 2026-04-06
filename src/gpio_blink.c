#include "gpio_blink.h"
#include <lgpio.h>
#include <stdio.h>

/*
 * Raspberry Pi 5 exposes GPIO through the RP1 south-bridge chip.
 * That chip appears as gpiochip4 in the kernel (index 4).
 */
#define GPIO_CHIP 4

static int g_handle = -1;

int gpio_blink_init(int pin) {
    g_handle = lgGpiochipOpen(GPIO_CHIP);
    if (g_handle < 0) {
        fprintf(stderr, "[Blink]: lgGpiochipOpen(gpiochip%d) failed: %d\n",
                GPIO_CHIP, g_handle);
        return -1;
    }

    /* Claim pin as push-pull output, initially LOW */
    int rc = lgGpioClaimOutput(g_handle, 0, pin, 0);
    if (rc < 0) {
        fprintf(stderr, "[Blink]: lgGpioClaimOutput(pin=%d) failed: %d\n", pin, rc);
        lgGpiochipClose(g_handle);
        g_handle = -1;
        return -1;
    }

    printf("[Blink]: GPIO %d ready on gpiochip%d\n", pin, GPIO_CHIP);
    return 0;
}

void gpio_blink_set_high(int pin) {
    if (g_handle >= 0) {
        lgGpioWrite(g_handle, pin, 1);
    }
}

void gpio_blink_set_low(int pin) {
    if (g_handle >= 0) {
        lgGpioWrite(g_handle, pin, 0);
    }
}

void gpio_blink_cleanup(int pin) {
    if (g_handle >= 0) {
        lgGpioWrite(g_handle, pin, 0);   /* ensure pin is LOW on exit */
        lgGpiochipClose(g_handle);
        g_handle = -1;
    }
}
