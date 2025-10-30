package com.scholarsphere.graphservice.repository;

import com.scholarsphere.graphservice.model.Paper;
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


    // paper->author
    @Query("""
        MATCH (a:Author)-[:AUTHORED]->(w:Work {id: $paperId})
        RETURN a
    """)
    List<Professor> findAuthorsByPaperId(@Param("paperId") String paperId);


    // author->coauthor
    @Query("""
    MATCH (a1:Author {id: $authorId})-[:AUTHORED]->(w:Work)<-[:AUTHORED]-(coauthor:Author)
    WHERE a1.id <> coauthor.id
    RETURN DISTINCT coauthor
    """)
    List<Professor> findCoauthorsByAuthorId(@Param("authorId") String authorId);



    // Get distinct subfields for a given author
    @Query("MATCH (a:Author {id: $authorId})-[:HAS_TOPIC]->(:Topic)-[:IN_SUBFIELD]->(s:Subfield) " +
       "RETURN DISTINCT s.displayName AS subfield ORDER BY subfield")
    List<String> findSubfieldsByAuthorId(String authorId);


    // Get papers by author and subfield
    @Query("""
        MATCH (a:Author {id: $authorId})
              -[:AUTHORED]->(w:Work)
              -[:IS_ABOUT_TOPIC]->(t:Topic)
              -[:IN_SUBFIELD]->(s:Subfield {displayName: $subfieldName})
        RETURN DISTINCT w.title AS title,
                        w.publicationYear AS year,
                        w.doi AS doi
        ORDER BY year DESC
        """)
    List<Paper> findPapersByAuthorIdAndSubfield(@Param("authorId") String authorId,
                                                @Param("subfieldName") String subfieldName);








    
}

