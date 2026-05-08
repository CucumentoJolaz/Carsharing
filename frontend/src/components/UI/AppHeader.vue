<template>
  <header class="header">
    <nav class="header__nav">
      <div class="header__container">
        <router-link to="/" class="header__link header__link--logo" active-class="header__link--active">
          Каршеринг
        </router-link>

        <button class="header__burger" @click="isMenuOpen = !isMenuOpen">
          <span></span>
          <span></span>
          <span></span>
        </button>

        <div class="header__menu" :class="{ 'header__menu--open': isMenuOpen }">
          <router-link to="/rent" class="header__link" active-class="header__link--active" @click="isMenuOpen = false">
            Аренда
          </router-link>
          <router-link to="/analytics" class="header__link" active-class="header__link--active"
                       @click="isMenuOpen = false">
            Аналитика
          </router-link>
          <router-link to="/" class="header__link" v-if="!isAuth" @click="isMenuOpen = false">
            Войти
          </router-link>
          <router-link to="/" class="header__link" v-else @click="logout">
            Выйти
          </router-link>
        </div>
      </div>
    </nav>
  </header>
</template>

<script>
export default {
  name: "AppHeader",
  data() {
    return {
      isAuth: false,
      isMenuOpen: false
    }
  },
  methods: {
    logout() {
      this.isAuth = false
      this.isMenuOpen = false
    }
  }
}
</script>

<style scoped>
.header {
  height: 60px;
  background: white;

  position: sticky;
  top: 0;
  z-index: 100;
}

.header__nav {
  border: 1px solid forestgreen;
  border-top: 0;
  border-radius: 0 0 16px 16px;
  max-width: 1200px;
  height: 100%;
  margin: 0 auto;
  padding: 0 30px;
  display: flex;
  align-items: center;
}

.header__container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  height: 100%;
}

.header__menu {
  display: flex;
  gap: 0;
  height: 100%;
}

.header__link {
  display: inline-flex;
  align-items: center;
  padding: 0 36px;
  height: 100%;
  text-decoration: none;
  font-weight: bold;
  color: #333;
  transition: all 0.2s;
}

.header__link:hover {
  background-color: #A4EDA8;
  color: black;
}

.header__link--active {
  color: forestgreen;
  position: relative;
}
.header__link--active::before {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 0%;
  width: 100%;
  height: 1px;
  background: forestgreen;
}

.header__link--logo {
  font-size: 1.75rem;
  color: forestgreen;
  line-height: 1;
  z-index: 99;
  background: white;
  width: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}



/* Бургер-меню */
.header__burger {
  display: none;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
}

.header__burger span {
  width: 25px;
  height: 2px;
  background: forestgreen;
  transition: 0.3s;
}

/* Адаптив для телефонов */
@media (max-width: 768px) {
  .header__nav {
    padding: 0;
    border: 0;
  }

  .header__burger {
    display: flex;
    margin: 15px;

  }

  .header__menu {
    position: fixed;
    top: 60px;
    left: -100%;
    width: 100%;
    height: calc(100vh - 60px);
    background: white;
    flex-direction: column;
    gap: 0;
    transition: left 0.3s;
    z-index: 99;
  }

  .header__menu--open {
    left: 0;
  }

  .header__link {
    padding: 16px 20px;
    height: auto;
    border-bottom: 1px solid #eee;
  }

  .header__link--logo {
    font-size: 1.5rem;
    color: forestgreen;
    line-height: 1;
    z-index: 100;
    padding: 0;
    padding-left: 20px;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    text-align: left;
  }


  .header__link:hover {
    background-color: #7cb342;
  }
  .header__container {
    border-bottom: 1px solid forestgreen;

  }
  .header__link--active {
    border-bottom: none;
    position: relative;
    border-bottom: 1px solid forestgreen;
  }

}
</style>