<script setup lang="ts">
import Button from 'primevue/button'
import DynamicDialog from 'primevue/dynamicdialog'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Toolbar from 'primevue/toolbar'

import { useDialog } from 'primevue/usedialog'

import { nextTick, ref } from 'vue'

import CreateCredentialsForm from '@/components/settings/CreateCredentialsForm.vue'
import CredeltialsDataList from '@/components/settings/CredentialsDataList.vue'
import type { DynamicDialogInstance } from 'primevue/dynamicdialogoptions'
import { useSettingsStore, type SettingsStore } from '@/stores/settingsStore'

const dialog = useDialog()

const dialogRef = ref<DynamicDialogInstance>()

const store = useSettingsStore() as SettingsStore

const couchbaseLink = ref<string>(import.meta.env.VITE_APP_COUCHBASE_URL)

const tabValue = ref('0')

const dialogDefaultProps = {
  header: 'Product List',
  style: {
    width: '50vw',
  },
  breakpoints: {
    '960px': '75vw',
    '640px': '90vw',
  },
  modal: true,
}

// ACTIONS

const displayCreateCredentialDialog = () => {
  const dialogSpecs = {
    props: { ...dialogDefaultProps, header: 'New Data Source' },
    templates: {},
    onClose: async (result: any) => {
      store.setUpdateTrigger(true)
      await nextTick() // Ensures Vue processes the change
    },
  }

  dialogRef.value = dialog.open(CreateCredentialsForm, dialogSpecs)
}
</script>

<template>
  <div id="container" class="flex flex-col items-center w-full bg-stone-100">
    <DynamicDialog />
    <div
      id="row-1"
      class="card w-[80%] mt-10 shadow-md flex justify-center items-center py-10 bg-white"
    >
      <i class="pi pi-cog text-3xl text-primary-500 mr-5"></i>
      <p class="font-abel text-3xl text-primary-500 font-bold">Storage Settings</p>
    </div>

    <div
      class="card w-[80%] flex-1 min-h-0 flex flex-col overflow-hidden shadow-md my-10 overflow-hidden"
    >
      <Tabs v-model:value="tabValue" class="flex-1 flex flex-col min-h-0" lazy select-on-focus>
        <TabList class="bg-none">
          <Tab value="0">Data Source Management</Tab>
          <Tab value="1">Application Database</Tab>
        </TabList>
        <TabPanels class="flex-1 flex flex-col min-h-0">
          <TabPanel value="0" class="flex-1 flex flex-col overflow-hidden p-0 gap-10">
            <div class="w-full flex-1 overflow-auto p-10">
              <Toolbar class="mb-4 py-3 px-5">
                <template #start>
                  <strong>Data Sources:</strong>
                </template>

                <template #end>
                  <Button
                    size="small"
                    v-tooltip.bottom="'New source'"
                    class="py-1 px-3"
                    @click="displayCreateCredentialDialog()"
                  >
                    <i class="pi pi-plus mr-2"></i>
                    <span class="hidden sm:inline">New Source</span>
                  </Button>
                </template>
              </Toolbar>

              <CredeltialsDataList />
            </div>
          </TabPanel>
          <TabPanel value="1" class="flex-1 flex flex-col overflow-hidden p-0 gap-10">
            <div class="w-full flex items-center p-2">
              <strong>To access the database directly using your user login</strong>
              <Button
                as="a"
                :href="couchbaseLink"
                label="click here"
                size="small"
                link
                target="_blank"
                rel="noopener noreferrer"
              />
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>
  </div>
</template>
