// webpack.config.js / rspack.config.js

// You can leverage your IDE's Intellisense (autocompletion, type check, etc.) with the helper function `defineReactCompilerLoaderOption`:
const { defineReactCompilerLoaderOption, reactCompilerLoader } = require('react-compiler-webpack');

module.exports = {
  module: {
    rules: [
      {
        test: /\.[mc]?[jt]sx?$/i,
        exclude: /node_modules/,
        use: [
          // babel-loader, swc-loader, esbuild-loader, or anything you like to transpile JSX should go here.
          // If you are using rspack, the rspack's buiilt-in react transformation is sufficient.
          // { loader: 'swc-loader' },
          //
          // Now add reactCompilerLoader
          {
            loader: reactCompilerLoader,
            options: defineReactCompilerLoaderOption({
              // React Compiler options goes here
            })
          }
        ]
      }
    ]
  }
};