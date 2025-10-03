package com.scholarsphere.gateway.filters;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;


import java.time.Duration;

@Component
public class CustomPopulateGlobalFilter implements GlobalFilter, Ordered {

    private final WebClient webClient;
    private static final Logger logger = LoggerFactory.getLogger(CustomPopulateGlobalFilter.class);

    public CustomPopulateGlobalFilter(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.baseUrl("http://scrappy:8083").build();
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Only intercept scrappy-service paths
        if (path.startsWith("/api/fetch-author") 
                || path.startsWith("/api/fetch-works-by-author")
                || path.startsWith("/api/fetch-work")) {

            String name = exchange.getRequest().getQueryParams().getFirst("name");
            logger.info("Scrappy request parameter name: {}", name);

            // If name exists, call scrappy service
            if (name != null && !name.isEmpty()) {
                return webClient.get()
                        .uri(uriBuilder -> uriBuilder.path(path).queryParam("name", name).build())
                        .retrieve()
                        .bodyToMono(String.class)
                        .timeout(Duration.ofSeconds(5))
                        .doOnNext(response -> System.out.println("Scrappy response: " + response))
                        .onErrorResume(e -> {
                            System.out.println("Scrappy call failed: " + e.getMessage());
                            return Mono.empty();
                        })
                        .then(chain.filter(exchange));
            }
        }

        // Otherwise just continue the chain
        return chain.filter(exchange);
    }

    @Override
    public int getOrder() {
        return -1;
    }
}
