<template>
  <div class="window__dimensions">
    <div class="window__content">
      <slot>
      </slot>
    </div>
  </div>
</template>

<script>
export default {
  name: "CentralWindow"
}
</script>

<style scoped>
.window__dimensions {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 50vh;
  max-height: 100vh;
  padding: 20px 30px 20px 20px;
}

.window__content {
  min-width: 800px;
  max-width: 1000px;
  margin: 30px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  border: 1px solid forestgreen;
  border-radius: 16px;
}

@media (max-width: 768px) {
  .window__dimensions {
    padding: 10px;
    align-items: flex-start;
  }

  .window__content {
    min-width: 400px;
    margin: 15px;
    padding: 20px;
  }

  .main__title {
    font-size: 1.3rem;
    margin: 0 0 20px 0;
  }

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

@media (max-width: 480px) {
  .window__content {
    min-width: 0;
    margin: 10px;
    padding: 15px;
  }

  .main__title {
    font-size: 1.1rem;
  }

  .main__menu-img-container {
    aspect-ratio: 16 / 9;
  }
}
</style>