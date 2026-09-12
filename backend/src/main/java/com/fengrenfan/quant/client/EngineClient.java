package com.fengrenfan.quant.client;

import com.fengrenfan.quant.config.QuantProperties;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

/** 调用 Python 量化引擎（FastAPI）的客户端。 */
@Component
public class EngineClient {

    private final RestClient restClient;

    public EngineClient(QuantProperties props) {
        this.restClient = RestClient.builder()
                .baseUrl(props.getEngineBaseUrl())
                .build();
    }

    public Map<String, Object> catalog() {
        return restClient.get().uri("/catalog").retrieve()
                .body(new ParameterizedTypeReference<>() {});
    }

    public Map<String, Object> symbols(String q, String type, int limit) {
        return restClient.get().uri(uriBuilder -> {
            uriBuilder.path("/symbols")
                    .queryParam("q", q)
                    .queryParam("limit", limit);
            if (type != null && !type.isBlank()) {
                uriBuilder.queryParam("type", type);
            }
            return uriBuilder.build();
        }).retrieve().body(new ParameterizedTypeReference<>() {});
    }

    public Map<String, Object> signal(String symbol, String strategy, String timeframe,
                                      int fast, int slow, String start, Integer costBps) {
        return restClient.get().uri(uriBuilder -> {
            uriBuilder.path("/signal")
                    .queryParam("symbol", symbol)
                    .queryParam("strategy", strategy)
                    .queryParam("timeframe", timeframe)
                    .queryParam("fast", fast)
                    .queryParam("slow", slow)
                    .queryParam("start", start);
            if (costBps != null) {
                uriBuilder.queryParam("cost_bps", costBps);
            }
            return uriBuilder.build();
        }).retrieve().body(new ParameterizedTypeReference<>() {});
    }

    public String health() {
        return restClient.get().uri("/health").retrieve().body(String.class);
    }
}
