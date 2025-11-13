const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    baseUrl: 'http://localhost:5000', // Assuming Flask app runs on 5000
    specPattern: 'cypress/e2e/**/*.spec.js',
    supportFile: false, // No support file needed for this simple test
    chromeWebSecurity: false,
  },
});