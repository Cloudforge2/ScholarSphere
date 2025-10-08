package storage

import (
	"context"
	"fmt"

	"github.com/Cloudforge2/scrappy/internal/domain"
	"github.com/neo4j/neo4j-go-driver/v6/neo4j"
)

// Repository defines the interface for database operations.
type Repository interface {
	SaveAuthor(ctx context.Context, author domain.Author) error
	SaveWork(ctx context.Context, work domain.Work) error
	Close(ctx context.Context) error
}

// neo4jRepository implements the Repository interface for Neo4j.
type neo4jRepository struct {
	driver neo4j.DriverWithContext
}

// NewNeo4jRepository creates a new repository and connects to the database.
func NewNeo4jRepository(uri, username, password string) (Repository, error) {
	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(username, password, ""))
	if err != nil {
		return nil, fmt.Errorf("could not create neo4j driver: %w", err)
	}

	// Verify the connection to the database is working.
	if err := driver.VerifyConnectivity(context.Background()); err != nil {
		return nil, fmt.Errorf("could not connect to neo4j: %w", err)
	}

	fmt.Println("Successfully connected to Neo4j")
	return &neo4jRepository{driver: driver}, nil
}

// Close closes the connection to the database.
func (r *neo4jRepository) Close(ctx context.Context) error {
	return r.driver.Close(ctx)
}

// SaveAuthor creates or updates an Author node and its Institution relationships.
func (r *neo4jRepository) SaveAuthor(ctx context.Context, author domain.Author) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		// Use MERGE to avoid creating duplicate authors.
		// Use ON CREATE SET for initial properties, ON MATCH SET to update existing ones.
		query := `
			MERGE (a:Author {id: $id})
			ON CREATE SET
				a.displayName = $displayName,
				a.orcid = $orcid,
				a.worksCount = $worksCount,
				a.citedByCount = $citedByCount
			ON MATCH SET
				a.displayName = $displayName,
				a.orcid = $orcid,
				a.worksCount = $worksCount,
				a.citedByCount = $citedByCount
		`
		parameters := map[string]interface{}{
			"id":           author.ID,
			"displayName":  author.DisplayName,
			"orcid":        author.Orcid,
			"worksCount":   author.WorksCount,
			"citedByCount": author.CitedByCount,
		}

		if _, err := tx.Run(ctx, query, parameters); err != nil {
			return nil, err
		}

		// Now, handle affiliations (the relationship to institutions)
		for _, affiliation := range author.Affiliations {
			instQuery := `
				MERGE (i:Institution {id: $instId})
				ON CREATE SET i.displayName = $instDisplayName
				MERGE (a:Author {id: $authorId})
				MERGE (a)-[:AFFILIATED_WITH]->(i)
			`
			instParams := map[string]interface{}{
				"instId":          affiliation.Institution.ID,
				"instDisplayName": affiliation.Institution.DisplayName,
				"authorId":        author.ID,
			}
			if _, err := tx.Run(ctx, instQuery, instParams); err != nil {
				return nil, err
			}
		}

		return nil, nil
	})

	return err
}

// SaveWork creates or updates a Work node and its relationship to Authors.
func (r *neo4jRepository) SaveWork(ctx context.Context, work domain.Work) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		query := `
			MERGE (w:Work {id: $id})
			ON CREATE SET
				w.title = $title,
				w.publicationYear = $pubYear,
				w.citedByCount = $citedByCount,
				w.doi = $doi
			ON MATCH SET
				w.title = $title,
				w.publicationYear = $pubYear,
				w.citedByCount = $citedByCount,
				w.doi = $doi
		`
		parameters := map[string]interface{}{
			"id":           work.ID,
			"title":        work.Title,
			"pubYear":      work.PublicationYear,
			"citedByCount": work.CitedByCount,
			"doi":          work.Doi,
		}
		if _, err := tx.Run(ctx, query, parameters); err != nil {
			return nil, err
		}

		// Handle the authorship relationships
		for _, authorship := range work.Authorships {
			authorQuery := `
				MERGE (a:Author {id: $authorId})
				ON CREATE SET a.displayName = $authorName
				MERGE (w:Work {id: $workId})
				MERGE (a)-[r:AUTHORED]->(w)
				SET r.position = $position
			`
			authorParams := map[string]interface{}{
				"authorId":   authorship.Author.ID,
				"authorName": authorship.Author.DisplayName,
				"workId":     work.ID,
				"position":   authorship.AuthorPosition,
			}
			if _, err := tx.Run(ctx, authorQuery, authorParams); err != nil {
				return nil, err
			}
		}
		return nil, nil
	})
	return err
}
