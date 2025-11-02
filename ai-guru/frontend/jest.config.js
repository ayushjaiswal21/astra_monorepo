module.exports = {
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: [
    'node_modules/(?!(marked)/)'
  ],
  moduleNameMapper: {
    '^marked$': '<rootDir>/node_modules/marked/lib/marked.cjs'
  }
};
