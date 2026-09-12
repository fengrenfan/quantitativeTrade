package com.fengrenfan.quant.controller;

import com.fengrenfan.quant.service.SignalService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/** 对外 API：/api/signal（信号+净值）、/api/catalog（元数据）、/api/health。 */
@RestController
@RequestMapping("/api")
public class SignalController {

    private final SignalService service;

    public SignalController(SignalService service) {
        this.service = service;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("status", "ok", "engine", service.engineHealth());
    }

    @GetMapping("/catalog")
    public ResponseEntity<?> catalog() {
        try {
            return ResponseEntity.ok(service.catalog());
        } catch (Exception e) {
            return ResponseEntity.status(502).body(Map.of("error", "引擎不可用：" + e.getMessage()));
        }
    }

    @GetMapping("/symbols")
    public ResponseEntity<?> symbols(
            @RequestParam(defaultValue = "") String q,
            @RequestParam(required = false) String type,
            @RequestParam(defaultValue = "30") int limit) {
        try {
            return ResponseEntity.ok(service.symbols(q, type, limit));
        } catch (Exception e) {
            return ResponseEntity.status(502).body(Map.of("error", "引擎不可用：" + e.getMessage()));
        }
    }

    @GetMapping("/signal")
    public ResponseEntity<?> signal(
            @RequestParam(defaultValue = "600519.SH") String symbol,
            @RequestParam(defaultValue = "dual_ma") String strategy,
            @RequestParam(defaultValue = "daily") String timeframe,
            @RequestParam(required = false) Integer fast,
            @RequestParam(required = false) Integer slow,
            @RequestParam(required = false) String start,
            @RequestParam(name = "cost_bps", required = false) Integer costBps) {
        try {
            return ResponseEntity.ok(
                    service.signal(symbol, strategy, timeframe, fast, slow, start, costBps));
        } catch (Exception e) {
            return ResponseEntity.status(502).body(Map.of("error", "引擎不可用：" + e.getMessage()));
        }
    }
}
