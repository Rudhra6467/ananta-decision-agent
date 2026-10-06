// Metro config: the default, plus one web-only swap (expo-secure-store -> browser storage) for livetrading247.com.
const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
const prev = config.resolver.resolveRequest;
config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === "web" && moduleName === "expo-secure-store") {
    return { type: "sourceFile", filePath: path.join(__dirname, "src/securestore.web.ts") };
  }
  return prev ? prev(context, moduleName, platform) : context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
