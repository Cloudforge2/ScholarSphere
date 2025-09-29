package com.scholarsphere.graphservice.model;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.RelationshipProperties;
import org.springframework.data.neo4j.core.schema.TargetNode;

import com.scholarsphere.graphservice.projection.DehydratedInstitution;

import lombok.AllArgsConstructor;
import lombok.Value;

import java.util.List;

@Value
@AllArgsConstructor
@RelationshipProperties
public class Affiliation {

    @Id @GeneratedValue
    Long id;

    List<Integer> years;

    @TargetNode
    DehydratedInstitution institution;
}