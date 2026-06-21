<template>
  <central-window>
    <central-title>Каршэринг с аналитикой</central-title>
    <div class="main__menu">
      <div class="main__menu-item">
        <div
            class="main__menu-img-container"
            @click="goToRentPage"
        >
          <img
              src='/src/images/car-main-4.webp'
              class="main__menu-img">
        </div>
        <custom-button
            class="main__btn"
            @click="goToRentPage"
        >
          Арендовать машину
        </custom-button>

      </div>
      <div class="main__menu-item">
        <div
            class="main__menu-img-container"
            @click="GoToAnalyticsPage"
        >
          <img
              src='/src/images/analytics-main-1.png'
              class="main__menu-img">

        </div>
        <custom-button
            class="main__btn"
            @click="GoToAnalyticsPage"
        >
          Аналитика
        </custom-button>
      </div>
    </div>

  </central-window>
</template>

<script>
export default {
  name: "Main",
  methods: {
    goToRentPage() {
      this.isMenuOpen = false // AppHeader.vue
      this.$router.push('/rent')
    },
    GoToAnalyticsPage() {
      this.isMenuOpen = false // AppHeader.vue
      this.$router.push('/analytics')
    }
  }
}
</script>

<style scoped>


.main__menu {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.main__menu-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.main__menu-img-container {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid forestgreen;
  width: 100%;
  aspect-ratio: 350 / 400;
  margin-bottom: 20px;
  border-radius: 12px;
  transition: transform 0.3s ease;
  cursor: pointer;
  box-sizing: border-box;
  padding: 20px;
  overflow: hidden;
}

.main__menu-img-container:hover {
  transform: scale(1.02);
}

.main__menu-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.main__btn {
  width: 100%;
  height: 60px;
}

@media (max-width: 640px) {
  .main__menu {
    flex-direction: column;
    gap: 30px;
  }

  .main__menu-item {
    width: 100%;
  }

  .main__menu-img-container {
    aspect-ratio: 4 / 3;
    margin-bottom: 15px;
  }
}


</style>