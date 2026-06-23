<template>
  <central-window>
    <central-title>Аренда автомобилей</central-title>

    <div class="rent__main">
      <div class="rent__car-list rent__custom-scroll" v-if="!rentalID">
        <div v-if="carListDownloaded" v-for="car in cars" :key="car.id" v-bind:id=car.id class="rent__car-list-item"
          v-bind:class="{ 'rent__car-list-item--active': activeCar === car }" v-on:click="chooseCar(car.id)">
          {{ carListName(car) }}
        </div>
        <div v-else class="rent__loading">
          <div class="rent__spinner"></div>
          <span>Загрузка автомобилей...</span>
        </div>
      </div>
      <div
        v-bind:class="rentalID ? 'rent__car-info-container--rent-active' : 'rent__car-info-container--rent-not-active'">
        <div class="rent__car-info-img">
          <img v-if="activeCar && activeCar.photo" v-bind:src="activeCar.photo" class="rent__car-image">
          <div v-else class="rent__no-image">Нет фото</div>
        </div>
        <div class="rent__car-info-text">
          <table class="rent__car-info-table">
            <tbody>
              <tr>
                <th>Название автомобиля</th>
                <td>{{ activeCar.brand }} {{ activeCar.model }}</td>
              </tr>
              <tr>
                <th>Год выпуска</th>
                <td>{{ activeCar.year }}</td>
              </tr>
              <tr>
                <th>Пробег</th>
                <td>{{ activeCar.odometer_reading }} км.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    <div v-if="errorMessage" class="rent__error">
      <span class="rent__error-icon">⚠</span>
      {{ errorMessage }}
    </div>
    <custom-button class="book__btn" :class="buttonColorClass" :disabled="isButtonLocked || errorMessage"
      @click="handleButtonClick">
      <span v-if="isButtonLocked" class="btn__spinner"></span>
      <span v-else>{{ carActionButtonText }}</span>
    </custom-button>
  </central-window>
</template>

<script>
import axios from 'axios'
import { carApi, rentalApi } from "@/api/carApi"

export default {
  name: "RentPage",
  mounted() {
    this.getCarList()
  },
  data() {
    return {
      cars: [],
      carListDownloaded: false,
      errorMessage: null,

      activeCar: {},

      rentalID: null,
      currentStatus: null, // null, 'booked', 'inspecting', 'active', 'completed'
      carActionButtonText: 'Забронировать автомобиль',
      isButtonLocked: true,
    }
  },
  computed: {
    buttonColorClass() {
      if (!this.currentStatus) return 'btn--book'
      if (this.currentStatus === 'booked') return 'btn--inspect'
      if (this.currentStatus === 'inspecting') return 'btn--rental'
      if (this.currentStatus === 'active') return 'btn--end'
      if (this.currentStatus === 'completed') return 'btn--book'
      return 'btn--book'
    }
  },
  watch: {
    activeCar: {
      handler(newActiveCar) {
            this.isButtonLocked = !newActiveCar || !newActiveCar.id
        },
        immediate: true
    },
  },
  methods: {
    informUserAboutError(error) {
      this.errorMessage = error
    },
    carListName(car) {
      return `${car.brand} ${car.model} (${car.year})`
    },
    chooseCar(chosenCarID) {
      this.activeCar = this.cars.find(car => car.id === chosenCarID)
    },
    async handleButtonClick() {
      if (this.isButtonLocked) return
      this.isButtonLocked = true
      try {
        await this.changeRentalStatus()
      } finally {
        this.isButtonLocked = false
      }
    },
    async changeRentalStatus() {
      if (!this.currentStatus) {
        await this.bookCar()
      } else if (this.currentStatus === 'booked') {
        await this.startInspection()
      } else if (this.currentStatus === 'inspecting') {
        await this.startRental()
      } else if (this.currentStatus === 'active') {
        await this.endRental()
      } else if (this.currentStatus === 'completed') {
        this.backToCarList()
      }
    },
    async bookCar() {
      try {
        const response = await rentalApi.bookCar(this.activeCar.id)
        this.rentalID = response.data.data.rental_id
        this.currentStatus = response.data.data.status
        this.carActionButtonText = response.data.data.new_button_text
      } catch (error) {
        if (error.response?.status === 409) {
          const message = error.response?.data?.detail || 'Произошла ошибка. Попробуйте снова.'
          this.informUserAboutError(message)
          console.error('Ошибка:', error)
        }


      }
    },
    async startInspection() {
      try {
        const response = await rentalApi.startInspection(this.activeCar.id, this.rentalID)
        this.rentalID = response.data.data.rental_id
        this.currentStatus = response.data.data.status
        this.carActionButtonText = response.data.data.new_button_text
      } catch (error) {
        const message = error.response?.data?.detail || 'Произошла ошибка. Попробуйте снова.'
        this.informUserAboutError(message)
        console.error('Ошибка:', error)
      }
    },
    async startRental() {
      try {
        const response = await rentalApi.startRental(this.activeCar.id, this.rentalID)
        this.rentalID = response.data.data.rental_id
        this.currentStatus = response.data.data.status
        this.carActionButtonText = response.data.data.new_button_text
      } catch (error) {
        const message = error.response?.data?.detail || 'Произошла ошибка. Попробуйте снова.'
        this.informUserAboutError(message)
        console.error('Ошибка:', error)
      }
    },
    async endRental() {
      try {
        const response = await rentalApi.endRental(this.activeCar.id, this.rentalID)
        this.rentalID = response.data.data.rental_id
        this.currentStatus = response.data.data.status
        this.carActionButtonText = response.data.data.new_button_text
      } catch (error) {
        const message = error.response?.data?.detail || 'Произошла ошибка. Попробуйте снова.'
        this.informUserAboutError(message)
        console.error('Ошибка:', error)
      }
    },
    backToCarList() {
      this.rentalID = null
      this.currentStatus = null
      this.carActionButtonText = 'Забронировать автомобиль'
    },
    async initiateRentalStatusOfUser() {
      try {
        const response = await rentalApi.getCurrentRental()
        const data = response.data
        if (data.data) {
          this.chooseCar(data.data.car)
          this.rentalID = data.data.id
          this.currentStatus = data.data.status
          this.carActionButtonText = data.data.button_text
        } else {
          this.activeCar = this.cars[0]
        }
      } catch (error) {
        this.activeCar = this.cars[0]
        if (error.response?.status === 404) {
          // 404 - нет активной аренды - это нормально
          console.log('Нет активной аренды')
        } else if (error.response?.status === 409) {
          this.informUserAboutError(error.response.data.detail)
        } else {
          console.error('Ошибка при проверке аренды:', error)
        }
      }
    },
    async getCarList() {
      try {
        const response = await carApi.getCars()
        this.cars = response.data
        this.carListDownloaded = true
        if (this.cars.length > 0) {
          await this.initiateRentalStatusOfUser()
        }
      } catch (error) {
        const message = error.response?.data?.detail || 'Произошла ошибка. Попробуйте снова.'
        this.informUserAboutError(message)
        console.error('Ошибка:', error)
      }
    },
  }
}
</script>

<style scoped>
/* ── Layout ────────────────────────────────────────────── */
.rent__main {
  width: 100%;
  max-width: 1000px;
  height: 80%;
  display: flex;
  flex-direction: row;
  box-sizing: border-box;
}

/* ── Car list ──────────────────────────────────────────── */
.rent__car-list {
  display: flex;
  flex-direction: column;
  width: 40%;
  min-width: 0;
  /* allow flex child to shrink below content size */
  overflow-y: scroll;
  overflow-x: hidden;
  height: 60vh;
  scrollbar-width: auto;
  scrollbar-color: forestgreen #f0f0f0;
  flex-shrink: 0;
}

.rent__car-list-item {
  width: 100%;
  border-bottom: 1px solid forestgreen;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  padding: 12px 20px 6px;
  cursor: pointer;
  transition: transform 0.2s ease, background-color 0.15s ease;
  word-break: break-word;
  overflow-wrap: break-word;
}

.rent__car-list-item:hover {
  background-color: #A9DBC5;
  transform: scale(1.02) translateY(-2px);
  border-top: 1px solid forestgreen;
}

.rent__car-list-item:active {
  background-color: #88C8B2;
}

.rent__car-list-item--active {
  background-color: #6BC8A4;
}

/* ── Car info panel ────────────────────────────────────── */
.rent__car-info-container--rent-not-active,
.rent__car-info-container--rent-active {
  padding: 0 15px 15px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  /* critical: prevents flex child overflow */
  overflow: hidden;
}

.rent__car-info-container--rent-not-active {
  width: 60%;
}

.rent__car-info-container--rent-active {
  width: 100%;
}

/* ── Image ─────────────────────────────────────────────── */
.rent__car-info-img {
  width: 100%;
  margin: 20px 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.rent__car-image {
  width: 100%;
  max-width: 500px;
  max-height: 400px;
  height: auto;
  object-fit: contain;
  border: 1px solid black;
  border-radius: 0 16px 0 16px;
  display: block;
}

/* ── Info table ────────────────────────────────────────── */
.rent__car-info-text {
  width: 100%;
  font-size: clamp(0.9rem, 2.5vw, 1.25rem);
  /* fluid font instead of fixed x-large */
  box-sizing: border-box;
}

.rent__car-info-table {
  width: 100%;
  table-layout: fixed;
  /* columns respect their container width */
  border-collapse: collapse;
}

.rent__car-info-table th,
.rent__car-info-table td {
  word-break: break-word;
  overflow-wrap: break-word;
  padding: 6px 4px;
}

.rent__car-info-table th {
  text-align: left;
  width: 55%;
}

.rent__car-info-table td {
  text-align: right;
  width: 45%;
}

.rent__car-info-table tr {
  border-bottom: 1px solid black;
}

/* ── Action button ─────────────────────────────────────── */
.book__btn {
  width: 100%;
  height: 60px;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 6px;
  transition: background-color 0.2s ease, transform 0.1s ease, opacity 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
}

.book__btn:active:not(:disabled) {
  transform: scale(0.98);
}

.book__btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

/* Состояния: "Забронировать" / "Вернуться к списку" — зелёный (существующая гамма) */
.btn--book {
  background-color: #3aaa6e;
}

.btn--book:hover:not(:disabled) {
  background-color: #27855a;
}

/* Состояние: "Начать осмотр" — голубой */
.btn--inspect {
  background-color: #4fa8d0;
}

.btn--inspect:hover:not(:disabled) {
  background-color: #2a7ba8;
}

/* Состояние: "Начать аренду" — янтарно-оранжевый */
.btn--rental {
  background-color: #e8952a;
}

.btn--rental:hover:not(:disabled) {
  background-color: #c47010;
}

/* Состояние: "Закончить аренду" — приглушённо-красный */
.btn--end {
  background-color: #d95b5b;
}

.btn--end:hover:not(:disabled) {
  background-color: #b03030;
}

/* ── Spinner (пока кнопка заблокирована) ───────────────── */
.btn__spinner {
  width: 22px;
  height: 22px;
  border: 3px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.rent__error {
  width: 100%;
  box-sizing: border-box;
  margin: 12px 0 8px;
  padding: 12px 16px;
  background-color: #fff0f0;
  border: 1px solid #d95b5b;
  border-left: 4px solid #d95b5b;
  border-radius: 4px;
  color: #8b1a1a;
  font-size: 0.95rem;
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.rent__error-icon {
  flex-shrink: 0;
  font-size: 1.1rem;
  margin-top: 1px;
}

/* ── Mobile ────────────────────────────────────────────── */
@media (max-width: 640px) {
  .rent__main {
    flex-direction: column;
    height: auto;
  }

  .rent__car-list {
    width: 100%;
    height: 35vh;
  }

  .rent__car-info-container--rent-not-active,
  .rent__car-info-container--rent-active {
    width: 100%;
    padding: 0 8px 10px;
  }

  .rent__car-info-img {
    margin: 12px 0;
  }

  .rent__car-image {
    max-height: 220px;
  }

  .rent__car-info-text {
    font-size: 0.95rem;
  }

  .book__btn {
    height: 52px;
    font-size: 0.95rem;
  }
}

.rent__loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  gap: 10px;
}

.rent__spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid forestgreen;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}
</style>