package com.scholarsphere.graphservice;

import java.util.Map;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "com.scholarsphere.graphservice")
public class GraphServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(GraphServiceApplication.class, args);
	}
}




