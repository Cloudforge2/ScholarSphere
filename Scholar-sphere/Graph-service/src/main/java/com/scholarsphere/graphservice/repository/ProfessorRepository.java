package com.scholarsphere.graphservice.repository;

import com.scholarsphere.graphservice.model.Professor;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.*;

 @Repository
public interface ProfessorRepository extends Neo4jRepository<Professor, String> {


    Optional<Professor> findById(String id);
   
    List<Professor> findByDisplayName(String displayName);

    @Query("MATCH (a:Author {id: $id}) RETURN count(a) > 0")
    boolean existsByAuthorId(@Param("id") String id);

    
}

