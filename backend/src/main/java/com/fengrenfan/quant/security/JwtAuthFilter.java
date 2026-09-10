package com.fengrenfan.quant.security;

import com.fengrenfan.quant.config.QuantProperties;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.SecretKey;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * 复用博客 JWT 登录态的鉴权过滤器（HS256）。
 * 仅当 quant.auth-enabled=true 且密钥 >=32 字节时生效；/api/health、/api/catalog 放行。
 */
public class JwtAuthFilter extends OncePerRequestFilter {

    private final boolean enabled;
    private final SecretKey key;

    public JwtAuthFilter(QuantProperties props) {
        this.enabled = props.isAuthEnabled();
        String secret = props.getJwtSecret() == null ? "" : props.getJwtSecret();
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        this.key = bytes.length >= 32 ? Keys.hmacShaKeyFor(bytes) : null;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return path.endsWith("/api/health") || path.endsWith("/api/catalog");
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (!enabled || key == null) {
            chain.doFilter(request, response);
            return;
        }
        String auth = request.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                Jwts.parser().verifyWith(key).build().parseSignedClaims(auth.substring(7));
                chain.doFilter(request, response);
                return;
            } catch (Exception ignored) {
                // 令牌无效 → 返回 401
            }
        }
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write("{\"error\":\"unauthorized\"}");
    }
}
