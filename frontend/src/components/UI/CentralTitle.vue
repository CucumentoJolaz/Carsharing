<template>
  <h1 class="central__title">
    <slot></slot>
  </h1>
</template>

<script>
export default {
  name: "CentralTitle"
}
</script>

<style scoped>
.central__title {
  margin: 0 0 15px 0;
  text-align: center;
  font-size: 1.8rem;
  padding-bottom: 15px;
  border-bottom: 1px solid forestgreen;
}

@media (max-width: 768px) {
  .central__title {
    font-size: 1.3rem;
    margin: 0 0 20px 0;
  }

}

</style>