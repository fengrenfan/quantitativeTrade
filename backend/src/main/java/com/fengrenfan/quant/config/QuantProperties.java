package com.fengrenfan.quant.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** 网关配置：引擎地址、默认回测参数、缓存、鉴权开关。 */
@ConfigurationProperties(prefix = "quant")
public class QuantProperties {

    /** Python 量化引擎地址 */
    private String engineBaseUrl = "http://localhost:8000";

    /** 默认回测起始日 */
    private String defaultStart = "2021-01-01";

    /** 默认交易成本（万分之） */
    private int costBps = 10;

    /** 信号缓存秒数 */
    private long cacheTtlSeconds = 600;

    /** 是否启用 JWT 鉴权（复用博客登录态） */
    private boolean authEnabled = false;

    /** JWT 密钥（HS256，>=32 字节），从环境变量注入 */
    private String jwtSecret = "";

    public String getEngineBaseUrl() {
        return engineBaseUrl;
    }

    public void setEngineBaseUrl(String engineBaseUrl) {
        this.engineBaseUrl = engineBaseUrl;
    }

    public String getDefaultStart() {
        return defaultStart;
    }

    public void setDefaultStart(String defaultStart) {
        this.defaultStart = defaultStart;
    }

    public int getCostBps() {
        return costBps;
    }

    public void setCostBps(int costBps) {
        this.costBps = costBps;
    }

    public long getCacheTtlSeconds() {
        return cacheTtlSeconds;
    }

    public void setCacheTtlSeconds(long cacheTtlSeconds) {
        this.cacheTtlSeconds = cacheTtlSeconds;
    }

    public boolean isAuthEnabled() {
        return authEnabled;
    }

    public void setAuthEnabled(boolean authEnabled) {
        this.authEnabled = authEnabled;
    }

    public String getJwtSecret() {
        return jwtSecret;
    }

    public void setJwtSecret(String jwtSecret) {
        this.jwtSecret = jwtSecret;
    }
}
