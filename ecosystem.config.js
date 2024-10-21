// Delete if not using redis
const redisEnv = {
  REDIS_HOST: "127.0.0.1",
  REDIS_PORT: "6379",
  REDIS_DB: "0",
};

const androidEnv = {
  ANDROID_HOME: "$HOME/Library/Android/sdk",
};

module.exports = {
  apps: [
    // Delete entry if not using redis
    {
      name: "redis",
      script: "./redis.sh",
    },
    {
      name: "appium",
      script: "./appium.sh",
      env: {
        ...androidEnv,
      },
    },
    {
      name: "game-bot",
      cwd: "./game-bot",
      script: "start.sh",
      env: {
        ...androidEnv,
        // Delete if not using redis
        ...redisEnv,
        CONFIG_SOURCE: "redis",
      },
    },
  ],
};
