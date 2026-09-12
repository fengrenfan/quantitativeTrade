package com.fengrenfan.quant.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fengrenfan.quant.client.EngineClient;
import com.fengrenfan.quant.config.QuantProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Map;

/**
 * 薄网关业务层：调用 Python 引擎，并用 Redis 缓存结果（复用博客底座）。
 * Redis 不可用时自动降级为直连引擎，不影响功能。
 */
@Service
public class SignalService {

    private static final Logger log = LoggerFactory.getLogger(SignalService.class);

    private final EngineClient engine;
    private final QuantProperties props;
    private final StringRedisTemplate redis;
    private final ObjectMapper mapper = new ObjectMapper();

    public SignalService(EngineClient engine, QuantProperties props, StringRedisTemplate redis) {
        this.engine = engine;
        this.props = props;
        this.redis = redis;
    }

    public Map<String, Object> catalog() {
        return engine.catalog();
    }

    public Map<String, Object> symbols(String q, String type, int limit) {
        return engine.symbols(q, type, limit);
    }

    public String engineHealth() {
        try {
            engine.health();
            return "up";
        } catch (Exception e) {
            return "down";
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> signal(String symbol, String strategy, String timeframe,
                                      Integer fast, Integer slow, String start, Integer costBps) {
        int f = fast != null ? fast : 5;
        int s = slow != null ? slow : 20;
        String st = (start != null && !start.isBlank()) ? start : props.getDefaultStart();
        int cb = costBps != null ? costBps : props.getCostBps();

        String key = String.format("quant:signal:%s:%s:%s:%d:%d:%s:%d",
                symbol, strategy, timeframe, f, s, st, cb);

        Map<String, Object> cached = readCache(key);
        if (cached != null) {
            return cached;
        }

        Map<String, Object> res = engine.signal(symbol, strategy, timeframe, f, s, st, cb);
        writeCache(key, res);
        return res;
    }

    private Map<String, Object> readCache(String key) {
        try {
            String json = redis.opsForValue().get(key);
            if (json != null) {
                Map<String, Object> cached = mapper.readValue(json, Map.class);
                // 历史上可能缓存过空结果（如引擎拉数失败），当作未命中，避免长时间返回空
                if (!isEmptyResult(cached)) {
                    return cached;
                }
                redis.delete(key);
            }
        } catch (Exception e) {
            log.debug("Redis 读缓存跳过：{}", e.getMessage());
        }
        return null;
    }

    private void writeCache(String key, Map<String, Object> res) {
        if (isEmptyResult(res)) {
            log.debug("结果为空（bars=0），跳过写入缓存");
            return;
        }
        try {
            redis.opsForValue().set(key, mapper.writeValueAsString(res),
                    Duration.ofSeconds(props.getCacheTtlSeconds()));
        } catch (Exception e) {
            log.debug("Redis 写缓存跳过：{}", e.getMessage());
        }
    }

    private boolean isEmptyResult(Map<String, Object> res) {
        if (res == null) {
            return true;
        }
        Object metrics = res.get("metrics");
        if (metrics instanceof Map<?, ?> m) {
            Object bars = m.get("bars");
            if (bars instanceof Number n) {
                return n.intValue() == 0;
            }
        }
        return false;
    }
}
