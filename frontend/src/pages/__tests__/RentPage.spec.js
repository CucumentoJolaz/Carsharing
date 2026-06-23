// src/pages/__tests__/RentPage.spec.js
// Component тесты для RentPage.vue
import { describe, test, expect, vi, beforeEach, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RentPage from '../RentPage.vue'
import CentralWindow from '@/components/UI/CentralWindow.vue'
import CentralTitle from '@/components/UI/CentralTitle.vue'
import CustomButton from '@/components/UI/CustomButton.vue'

// ============================================
// Мок API
// ============================================
vi.mock('@/api/carApi', () => ({
    carApi: {
        getCars: vi.fn()
    },
    rentalApi: {
        getCurrentRental: vi.fn(),
        bookCar: vi.fn(),
        startInspection: vi.fn(),
        startRental: vi.fn(),
        endRental: vi.fn(),
    }
}))


const components = {
    CentralWindow,
    CentralTitle,
    CustomButton
}


describe('RentPage', () => {
    // Очищаем перед каждым тестом
    beforeEach(() => {
        vi.clearAllMocks()
    })

    // ============================================
    // ТЕСТ 1: Рендеринг страницы
    // ============================================

    test('should render the page component', () => {
        const wrapper = mount(RentPage, {
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })
        expect(wrapper.exists()).toBe(true)
        expect(wrapper.text()).toContain('Аренда автомобилей')
    })


    // ============================================
    // ТЕСТ 2: Показывает спиннер загрузки
    // ============================================
    test('shows loading spinner when cars are not loaded', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: false
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        expect(wrapper.find('.rent__spinner').exists()).toBe(true)
        expect(wrapper.text()).toContain('Загрузка автомобилей...')
    })

    // ============================================
    // ТЕСТ 3: Отображает список автомобилей
    // ============================================
    test('displays car list when loaded', async () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: true,
                    cars: [
                        { id: 1, brand: 'Toyota', model: 'Camry', year: 2020 },
                        { id: 2, brand: 'Honda', model: 'Civic', year: 2021 }
                    ]
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })
        await wrapper.vm.$nextTick()

        const carItems = wrapper.findAll('.rent__car-list-item')
        expect(carItems).toHaveLength(2)
        expect(carItems[0].text()).toContain('Toyota Camry (2020)')
        expect(carItems[1].text()).toContain('Honda Civic (2021)')
    })
    // ============================================
    // ТЕСТ 4: Выбор автомобиля по клику
    // ============================================
    test('selects a car when clicked', async () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: true,
                    cars: [
                        { id: 1, brand: 'Toyota', model: 'Camry', year: 2020 },
                        { id: 2, brand: 'Honda', model: 'Civic', year: 2021 }
                    ],
                    activeCar: {}
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        const firstCar = wrapper.findAll('.rent__car-list-item')[0]
        await firstCar.trigger('click')

        expect(wrapper.vm.activeCar.id).toBe(1)
        expect(wrapper.vm.activeCar.brand).toBe('Toyota')
    })

    // ============================================
    // ТЕСТ 5: Отображает информацию о выбранном авто
    // ============================================
    test('displays car info when car is selected', async () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: true,
                    cars: [
                        { id: 1, brand: 'Toyota', model: 'Camry', year: 2020, odometer_reading: 50000 }
                    ],
                    activeCar: { id: 1, brand: 'Toyota', model: 'Camry', year: 2020, odometer_reading: 50000 }
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })
        await wrapper.vm.$nextTick()

        expect(wrapper.text()).toContain('Toyota')
        expect(wrapper.text()).toContain('Camry')
        expect(wrapper.text()).toContain('2020')
        expect(wrapper.text()).toContain('50000')
    })

    // ============================================
    // ТЕСТ 6: Меняет текст кнопки в зависимости от статуса
    // ============================================
    test('changes button text based on rental status', async () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: true,
                    cars: [{ id: 1, brand: 'Toyota', model: 'Camry', year: 2020 }],
                    activeCar: { id: 1, brand: 'Toyota', model: 'Camry', year: 2020 },
                    currentStatus: null,
                    carActionButtonText: 'Забронировать автомобиль'
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        const button = wrapper.find('button')
        console.log('Найдена кнопка:', wrapper.find('button').exists())
        console.log('HTML кнопки:', wrapper.find('button').html())
        console.log('Текст кнопки:', wrapper.find('button').text())

        expect(button.text()).toContain('Забронировать автомобиль')

        await wrapper.setData({
            currentStatus: 'booked',
            carActionButtonText: 'Начать осмотр'
        })
        expect(button.text()).toContain('Начать осмотр')

        await wrapper.setData({
            currentStatus: 'inspecting',
            carActionButtonText: 'Начать аренду'
        })
        expect(button.text()).toContain('Начать аренду')

        await wrapper.setData({
            currentStatus: 'active',
            carActionButtonText: 'Завершить аренду'
        })
        expect(button.text()).toContain('Завершить аренду')

        await wrapper.setData({
            currentStatus: 'completed',
            carActionButtonText: 'Вернуться к списку'
        })
        expect(button.text()).toContain('Вернуться к списку')
    })

    // ============================================
    // ТЕСТ 7: Кнопка блокируется во время загрузки
    // ============================================
    test('disables button when loading', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: false,
                    cars: [],
                    activeCar: {},
                    isButtonLocked: true
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        const button = wrapper.find('button')
        expect(button.attributes('disabled')).toBeDefined()
    })

    // ============================================
    // ТЕСТ 8: Показывает спиннер на кнопке при загрузке
    // ============================================
    test('shows spinner on button when loading', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: false,
                    cars: [],
                    activeCar: {},
                    isButtonLocked: true
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        expect(wrapper.find('.btn__spinner').exists()).toBe(true)
    })

    // ============================================
    // ТЕСТ 9: Показывает сообщение об ошибке
    // ============================================
    test('shows error message when error occurs', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    errorMessage: 'Машина уже забронирована'
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        expect(wrapper.find('.rent__error').exists()).toBe(true)
        expect(wrapper.text()).toContain('Машина уже забронирована')
    })

    // ============================================
    // ТЕСТ 10: Правильно форматирует название автомобиля
    // ============================================
    test('formats car name correctly', () => {
        const wrapper = mount(RentPage)
        const car = { brand: 'BMW', model: 'X5', year: 2022 }
        const result = wrapper.vm.carListName(car)
        expect(result).toBe('BMW X5 (2022)')
    })

    // ============================================
    // ТЕСТ 11: Скрывает список при активной аренде
    // ============================================
    test('hides car list when rental is active', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    rentalID: 123,
                    carListDownloaded: true,
                    cars: [{ id: 1, brand: 'Toyota', model: 'Camry', year: 2020 }]
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        expect(wrapper.find('.rent__car-list').exists()).toBe(false)
    })

    // ============================================
    // ТЕСТ 12: Кнопка disabled при отсутствии активного авто
    // ============================================
    test('button is disabled when no car is selected', () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    carListDownloaded: true,
                    cars: [{ id: 1, brand: 'Toyota', model: 'Camry', year: 2020 }],
                    activeCar: {}
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        const button = wrapper.find('button')
        expect(button.attributes('disabled')).toBeDefined()
    })

    // ============================================
    // ТЕСТ 13: Сброс аренды при возврате к списку
    // ============================================
    test('resets rental when going back to car list', async () => {
        const wrapper = mount(RentPage, {
            data() {
                return {
                    rentalID: 123,
                    currentStatus: 'completed',
                    carActionButtonText: 'Вернуться к списку'
                }
            },
            global: {
                components: {
                    CentralWindow,
                    CentralTitle,
                    CustomButton
                }
            }
        })

        await wrapper.vm.backToCarList()

        expect(wrapper.vm.rentalID).toBeNull()
        expect(wrapper.vm.currentStatus).toBeNull()
        expect(wrapper.vm.carActionButtonText).toBe('Забронировать автомобиль')
    })

    // ============================================
    // ТЕСТ 14: Обработка ошибки при загрузке списка
    // ============================================
    test('handles error when loading car list', async () => {
        const wrapper = mount(RentPage)

        // Имитируем ошибку в getCarList
        await wrapper.vm.getCarList()

        // Проверяем, что ошибка обработана
        // (зависит от вашей реализации)
        expect(wrapper.vm.carListDownloaded).toBe(false)
    })
})