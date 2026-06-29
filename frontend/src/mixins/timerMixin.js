// mixins/timerMixin.js
// Методы поставляемый в mixin предназначены для реализации интерфейса таймера и секундомера.
// Для использования в цикле аренды. RentPage.vue
export const timerMixin = {
    data() {
        return {
            timerValue: 0,
            timerInterval: null,
        }
    },
    methods: {
        startCountdown(seconds) {
            this.timerValue = seconds
            this.timerInterval = setInterval(() => {
                this.timerValue--
                this.onTimerTick?.(this.timerValue)
                if (this.timerValue <= 0) {
                    this.stop.Timer()
                    this.onTimerEnd?.()
                }
            }, 1000)
        },
    }
}