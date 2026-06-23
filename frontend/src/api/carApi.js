import axios from 'axios'

export const carApi = {
  getCars() {
    return axios.get('/api/v1/cars/')
  }
}

export const rentalApi = {
  getCurrentRental() {
    return axios.get('/api/v1/users/me/rental/')
  },

  bookCar(carId) {
    return axios.post(`/api/v1/cars/${carId}/rentals/`)
  },

  startInspection(carId, rentalId) {
    return axios.post(`/api/v1/cars/${carId}/rentals/${rentalId}/start-inspection/`)
  },

  startRental(carId, rentalId) {
    return axios.post(`/api/v1/cars/${carId}/rentals/${rentalId}/start-rental/`)
  },

  endRental(carId, rentalId) {
    return axios.post(`/api/v1/cars/${carId}/rentals/${rentalId}/end-rental/`)
  }
}