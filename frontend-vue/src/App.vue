<template>
  <LoginPage v-if="route.name === 'login'" />
  <AppLayout v-else />
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import LoginPage from '@/pages/LoginPage.vue'

const route = useRoute()
</script>
