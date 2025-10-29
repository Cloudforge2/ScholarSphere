package storage

import (
	"context" // ADDED: Need this for error comparison
	"fmt"
	"time"

	"github.com/Cloudforge2/scrappy/internal/domain" // Assumed package path
	"github.com/neo4j/neo4j-go-driver/v6/neo4j"
)

// Repository defines the interface for all database operations.
type Repository interface {
	SaveAuthor(ctx context.Context, author domain.Author) error
	SaveWork(ctx context.Context, work domain.Work) error
	Close(ctx context.Context) error
}

// neo4jRepository implements the Repository interface for Neo4j.
type neo4jRepository struct {
	driver neo4j.DriverWithContext
}

// NewNeo4jRepository creates a new repository and verifies the connection to the database.
func NewNeo4jRepository(uri, username, password string) (Repository, error) {
	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(username, password, ""))
	if err != nil {
		return nil, fmt.Errorf("could not create neo4j driver: %w", err)
	}
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

// SaveAuthor creates or updates an Author node with all its properties and relationships.
func (r *neo4jRepository) SaveAuthor(ctx context.Context, author domain.Author) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		query := `
			MERGE (a:Author {id: $id})
			ON CREATE SET
				a.displayName = $displayName,
				a.displayNameAlternatives = $displayNameAlternatives,
				a.orcid = $orcid,
				a.worksCount = $worksCount,
				a.citedByCount = $citedByCount,
				a.updatedDate = $updatedDate,
				a.lastFetched = $lastFetched
			ON MATCH SET
				a.displayName = $displayName,
				a.displayNameAlternatives = $displayNameAlternatives,
				a.orcid = $orcid,
				a.worksCount = $worksCount,
				a.citedByCount = $citedByCount,
				a.updatedDate = $updatedDate,
				a.lastFetched = $lastFetched
		`
		parameters := map[string]interface{}{
			"id":                      author.ID,
			"displayName":             author.DisplayName,
			"displayNameAlternatives": author.DisplayNameAlternatives,
			"orcid":                   author.Orcid,
			"worksCount":              author.WorksCount,
			"citedByCount":            author.CitedByCount,
			"updatedDate":             author.UpdatedDate,
			"lastFetched":             time.Now().UTC().Format(time.RFC3339),
		}
		if _, err := tx.Run(ctx, query, parameters); err != nil {
			return nil, fmt.Errorf("failed to save author node: %w", err)
		}

		for _, affiliation := range author.Affiliations {
			instQuery := `
				MERGE (i:Institution {id: $instId}) ON CREATE SET i.displayName = $instDisplayName
				MERGE (a:Author {id: $authorId})
				MERGE (a)-[:AFFILIATED_WITH]->(i)
			`
			instParams := map[string]interface{}{
				"instId":          affiliation.Institution.ID,
				"instDisplayName": affiliation.Institution.DisplayName,
				"authorId":        author.ID,
			}
			if _, err := tx.Run(ctx, instQuery, instParams); err != nil {
				return nil, fmt.Errorf("failed to save author affiliation: %w", err)
			}
		}

		// Create the Topic hierarchy relationships for the author
		fmt.Println("author topics:", len(author.Topics))
		for _, topic := range author.Topics {
			topicQuery := `
				// Find the author this topic belongs to
				MATCH (a:Author {id: $authorId})

				// Use MERGE to create the entire hierarchy path idempotently.
				// This ensures that "Computer Science" is created only once.
				MERGE (d:Domain {id: $domainId}) ON CREATE SET d.displayName = $domainName
				MERGE (f:Field {id: $fieldId}) ON CREATE SET f.displayName = $fieldName
				MERGE (s:Subfield {id: $subfieldId}) ON CREATE SET s.displayName = $subfieldName
				MERGE (t:Topic {id: $topicId}) ON CREATE SET t.displayName = $topicName

				// Merge the relationships between the hierarchy levels
				MERGE (t)-[:IN_SUBFIELD]->(s)
				MERGE (s)-[:IN_FIELD]->(f)
				MERGE (f)-[:IN_DOMAIN]->(d)

				// Finally, connect the author to the specific topic and set the paper count
				// as a property on the relationship.
				MERGE (a)-[r:HAS_TOPIC]->(t)
				SET r.paperCount = $count
			`
			topicParams := map[string]interface{}{
				"authorId":     author.ID,
				"count":        topic.Count,
				"topicId":      topic.ID,
				"topicName":    topic.DisplayName,
				"subfieldId":   topic.Subfield.ID,
				"subfieldName": topic.Subfield.DisplayName,
				"fieldId":      topic.Field.ID,
				"fieldName":    topic.Field.DisplayName,
				"domainId":     topic.Domain.ID,
				"domainName":   topic.Domain.DisplayName,
			}
			if _, err := tx.Run(ctx, topicQuery, topicParams); err != nil {
				return nil, fmt.Errorf("failed to save author topic hierarchy: %w", err)
			}
		}
		return nil, nil
	})
	return err
}

// SaveWork creates or updates a Work node with all its rich properties and relationships in a single transaction.
func (r *neo4jRepository) SaveWork(ctx context.Context, work domain.Work) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		// 1. Create or Update the Work node itself with its properties
		workQuery := `
			MERGE (w:Work {id: $id})
			ON CREATE SET
				w.title = $title, w.publicationYear = $pubYear, w.publicationDate = $publicationDate,
				w.citedByCount = $citedByCount, w.doi = $doi, w.isRetracted = $isRetracted,
				w.isOa = $isOa, w.pdfUrl = $pdfUrl
			ON MATCH SET
				w.title = $title, w.publicationYear = $pubYear, w.publicationDate = $publicationDate,
				w.citedByCount = $citedByCount, w.doi = $doi, w.isRetracted = $isRetracted,
				w.isOa = $isOa, w.pdfUrl = $pdfUrl
		`
		isOa := false
		pdfUrl := ""
		if work.BestOaLocation != nil {
			isOa = work.BestOaLocation.IsOa
			pdfUrl = work.BestOaLocation.PdfUrl
		}
		workParams := map[string]interface{}{
			"id": work.ID, "title": work.Title, "pubYear": work.PublicationYear,
			"publicationDate": work.PublicationDate, "citedByCount": work.CitedByCount,
			"doi": work.Doi, "isRetracted": work.IsRetracted, "isOa": isOa, "pdfUrl": pdfUrl,
		}
		if _, err := tx.Run(ctx, workQuery, workParams); err != nil {
			return nil, fmt.Errorf("failed to save work node: %w", err)
		}

		// 2. Create/Update Authorship relationships (enriched with institutions)
		for _, authorship := range work.Authorships {
			var instIds []string
			for _, inst := range authorship.Institutions {
				instIds = append(instIds, inst.ID)
			}
			authorQuery := `
				MERGE (a:Author {id: $authorId}) ON CREATE SET a.displayName = $authorName
				MERGE (w:Work {id: $workId})
				MERGE (a)-[r:AUTHORED]->(w)
				SET r.position = $position, r.institutionIds = $institutionIds
			`
			authorParams := map[string]interface{}{
				"authorId": authorship.Author.ID, "authorName": authorship.Author.DisplayName,
				"workId": work.ID, "position": authorship.AuthorPosition, "institutionIds": instIds,
			}
			if _, err := tx.Run(ctx, authorQuery, authorParams); err != nil {
				return nil, fmt.Errorf("failed to save authorship: %w", err)
			}
		}

		// 3. Create/Update Publication Venue relationship
		if work.PrimaryLocation != nil && work.PrimaryLocation.Source != nil {
			venueQuery := `
				MERGE (v:Venue {id: $venueId}) ON CREATE SET v.displayName = $venueName
				MERGE (w:Work {id: $workId})
				MERGE (w)-[:PUBLISHED_IN]->(v)
			`
			venueParams := map[string]interface{}{
				"workId": work.ID, "venueId": work.PrimaryLocation.Source.ID,
				"venueName": work.PrimaryLocation.Source.DisplayName,
			}
			if _, err := tx.Run(ctx, venueQuery, venueParams); err != nil {
				return nil, fmt.Errorf("failed to save venue relationship: %w", err)
			}
		}

		// 5. Create Topic relationships and their full hierarchy

		for _, topic := range work.Topics {
			topicQuery := `
				// Find the work this topic belongs to
				MATCH (w:Work {id: $workId})

				// Use MERGE to create the entire hierarchy path idempotently.
				// This ensures that "Computer Science" is created only once, for example.
				MERGE (d:Domain {id: $domainId}) ON CREATE SET d.displayName = $domainName
				MERGE (f:Field {id: $fieldId}) ON CREATE SET f.displayName = $fieldName
				MERGE (s:Subfield {id: $subfieldId}) ON CREATE SET s.displayName = $subfieldName
				MERGE (t:Topic {id: $topicId}) ON CREATE SET t.displayName = $topicName

				// Merge the relationships between the hierarchy levels
				MERGE (t)-[:IN_SUBFIELD]->(s)
				MERGE (s)-[:IN_FIELD]->(f)
				MERGE (f)-[:IN_DOMAIN]->(d)

				// Finally, connect the work to the specific topic and set the relevance score
				// on the relationship.
				MERGE (w)-[r:IS_ABOUT_TOPIC]->(t)
				SET r.score = $score
			`
			topicParams := map[string]interface{}{
				"workId":       work.ID,
				"topicId":      topic.ID,
				"topicName":    topic.DisplayName,
				"score":        topic.Score,
				"subfieldId":   topic.Subfield.ID,
				"subfieldName": topic.Subfield.DisplayName,
				"fieldId":      topic.Field.ID,
				"fieldName":    topic.Field.DisplayName,
				"domainId":     topic.Domain.ID,
				"domainName":   topic.Domain.DisplayName,
			}
			if _, err := tx.Run(ctx, topicQuery, topicParams); err != nil {
				return nil, fmt.Errorf("failed to save work topic hierarchy: %w", err)
			}
		}
		return nil, nil
	})
	return err
}
