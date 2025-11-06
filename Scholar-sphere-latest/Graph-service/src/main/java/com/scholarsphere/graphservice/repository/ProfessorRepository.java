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


// ✅ Get distinct topics for a given author (direct HAS_TOPIC relationship)
@Query("""
    MATCH (a:Author {id: $authorId})-[:HAS_TOPIC]->(t:Topic)
    RETURN DISTINCT t.displayName AS topic
    ORDER BY topic
    """)
List<String> findTopicsByAuthorId(String authorId);

// ✅ Get all papers for a given author and topic (linked via HAS_TOPIC)
@Query("""
    MATCH (a:Author {id: $authorId})-[:AUTHORED]->(w:Work)-[:IS_ABOUT_TOPIC]->(t:Topic {displayName: $topicName})
    RETURN DISTINCT w.id AS id,
                    w.title AS title,
                    w.publicationYear AS year,
                    w.doi AS doi
    ORDER BY year DESC
    """)
List<Paper> findPapersByAuthorIdAndTopic(@Param("authorId") String authorId,
                                         @Param("topicName") String topicName);

@Query("MATCH (a:Author {id: $id}) RETURN a.fullyIngested = true AS ingested")
Boolean isFullyIngested(@Param("id") String id);

@Query("MATCH (a:Author {id: $id}) RETURN a.lastFetched")
String getLastFetchedDate(@Param("id") String id);



}

