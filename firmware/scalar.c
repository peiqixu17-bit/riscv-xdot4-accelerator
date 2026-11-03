/* Task015 S1: generic input pointers, no data-dependent specialization.
 * signed char may alias the original packed buffer. int product is bounded;
 * unsigned accumulation explicitly defines modulo-2^32 semantics. */
#include <stdint.h>
__attribute__((noinline)) uint32_t s1_kernel(const signed char *a,
                                          const signed char *b,
                                          uint32_t words) {
    uint32_t sum = 0;
    for (uint32_t i = 0; i < words * 4u; ++i)
        sum += (uint32_t)((int32_t)a[i] * (int32_t)b[i]);
    return sum;
}
