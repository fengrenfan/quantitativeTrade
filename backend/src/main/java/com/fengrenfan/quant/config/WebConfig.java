package com.fengrenfan.quant.config;

import com.fengrenfan.quant.security.JwtAuthFilter;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig {

    /** 跨域：开发期放开，生产可收紧为博客域名。 */
    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                        .allowedOriginPatterns("*")
                        .allowedMethods("GET", "POST", "OPTIONS")
                        .allowedHeaders("*");
            }
        };
    }

    /** 注册 JWT 鉴权过滤器，仅拦截 /api/*。 */
    @Bean
    public FilterRegistrationBean<JwtAuthFilter> jwtFilter(QuantProperties props) {
        FilterRegistrationBean<JwtAuthFilter> reg = new FilterRegistrationBean<>();
        reg.setFilter(new JwtAuthFilter(props));
        reg.addUrlPatterns("/api/*");
        reg.setOrder(1);
        return reg;
    }
}
