#if defined(__GNUC__)

#include <pthread.h>
#include <stdint.h>

/* Some architectures do not support __sync_add_and_fetch_8 */
#if (__mips == 32) || (__nios2__) || (defined(__PPC__) && !defined(__GCC_HAVE_SYNC_COMPARE_AND_SWAP_8))

struct PthMutex {
	pthread_mutex_t m;
	PthMutex() { pthread_mutex_init(&m, 0); }
	~PthMutex() { pthread_mutex_destroy(&m); }
	void lock() { pthread_mutex_lock(&m); }
	void unlock() { pthread_mutex_unlock(&m); }
};

static const size_t kSwapLockCount = 32;
static PthMutex s_swapLocks[kSwapLockCount];
static inline PthMutex& getSwapLock(const volatile uint64_t* addr) {
	return s_swapLocks[(reinterpret_cast<intptr_t>(addr) >> 3U) % kSwapLockCount];
}
static uint64_t atomicStep(uint64_t volatile* addend, uint64_t step) {
	PthMutex& mutex = getSwapLock(addend);
	mutex.lock();
	uint64_t value = *addend + step;
	*addend = value;
	mutex.unlock();
	return value;
}

extern "C" uint64_t __sync_add_and_fetch_8(void volatile* addend, uint64_t value) {
	return atomicStep((uint64_t*)addend, value);
}
extern "C" uint64_t __sync_sub_and_fetch_8(void volatile* addend, uint64_t value) {
	return atomicStep((uint64_t*)addend, -value);
}
#endif

#endif // __GNUC__
