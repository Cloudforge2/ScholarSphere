package com.example.Scholarsphere.DTO;

public  class TopicStat {
    private String topic;
    private Long count;

    public TopicStat(String topic, Long count) {
        this.topic = topic;
        this.count = count;
    }

    // Getters are required for JSON serialization
    public String getTopic() { return topic; }
    public Long getCount() { return count; }
    
}
