package com.scholarsphere.graphservice.repository;

import com.scholarsphere.graphservice.model.Professor;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

 @Repository
// public interface ProfessorRepository extends Neo4jRepository<Professor, String> {

//     // Custom query: fetch professor and expand authored papers
//     @Query("""
//            MATCH (p:Professor {id: $id})-[:AUTHORED]->(paper:Paper)
//            RETURN p, collect(paper) as papers
//            """)
//     Optional<Professor> findProfessorWithPapers(String id);
// }
public interface ProfessorRepository extends Neo4jRepository<Professor, String> {

    // Fetch author and all their works
    @Query("""
           MATCH (a:Author {id: $id})-[:AUTHORED]->(w:Work)
           RETURN a, collect(w) as papers
           """)
    Optional<Professor> findAuthorWithWorks(String id);
    
    // @Query("""
    //    MATCH (a:Author {displayName: $displayName})-[:AUTHORED]->(w:Work)
    //    RETURN a, collect(w) as papers
    //    LIMIT 1
    //    """)
    //Optional<Professor> findAuthorWithWorksByName(String displayName);
    //Optional<Professor> findByDisplayName(String displayName);
    List<Professor> findByDisplayName(String displayName);
    

}