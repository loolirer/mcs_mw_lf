target_sources(${LF_MAIN_TARGET} PRIVATE gpio_blink.c)
target_link_libraries(${LF_MAIN_TARGET} PUBLIC lgpio)
