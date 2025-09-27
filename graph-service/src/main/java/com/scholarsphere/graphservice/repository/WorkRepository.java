package com.scholarsphere.graphservice.repository;

import com.scholarsphere.graphservice.model.Professor;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface WorkRepository extends Neo4jRepository<Professor, String> {
    
}
