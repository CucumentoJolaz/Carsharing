<template>
    <button class="btn">
    <slot>

    </slot>
  </button>
</template>

<script>
export default {
  name: "CustomButton"
}
</script>

<style scoped>
.btn {
  margin-top: 15px;
  padding: 10px 15px;
  background: none;
  background-color: #EBFCEB;
  border-radius: 6px;
  transition: background-color 0.2s ease, transform 0.1s ease, opacity 0.2s ease;
  border: 1px solid forestgreen;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}
.btn:hover {
  background-color: forestgreen;
  border: 1px solid forestgreen;
  color: white;
}

.btn:hover:not(:disabled) {
  background-color: #27855a;
}

.btn:active  {
  background-color: #68BA7F;
  transition-duration: 0s;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>