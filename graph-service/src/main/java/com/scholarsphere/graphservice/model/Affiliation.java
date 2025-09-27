package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.RelationshipProperties;
import org.springframework.data.neo4j.core.schema.TargetNode;

import java.util.List;

@RelationshipProperties
public class Affiliation {

    private final List<Integer> years;
    @Id
    @GeneratedValue // <-- ADD THESE TWO ANNOTATIONS
    private Long id;
    @TargetNode
    private final Institution institution;

    // Constructor, getters
    public Affiliation(List<Integer> years, Institution institution) {
        this.years = years;
        this.institution = institution;
    }

    public List<Integer> getYears() {
        return years;
    }

    public Institution getInstitution() {
        return institution;
    }
}