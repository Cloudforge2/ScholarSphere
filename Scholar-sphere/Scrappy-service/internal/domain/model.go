package domain

import "time"

// --- Core Entities ---

// Author corresponds to the Author entity from OpenAlex.
type Author struct {
	ID                      string                   `json:"id"`
	DisplayName             string                   `json:"display_name"`
	DisplayNameAlternatives []string                 `json:"display_name_alternatives"`
	Orcid                   string                   `json:"orcid"`
	CitedByCount            int                      `json:"cited_by_count"`
	WorksCount              int                      `json:"works_count"`
	WorksApiUrl             string                   `json:"works_api_url"`
	CreatedDate             string                   `json:"created_date"`
	UpdatedDate             string                   `json:"updated_date"`
	CountsByYear            []CountsByYear           `json:"counts_by_year"`
	LastKnownInstitutions   []*DehydratedInstitution `json:"last_known_institutions"`
	Affiliations            []Affiliation            `json:"affiliations"`
	Ids                     map[string]string        `json:"ids"`
	SummaryStats            AuthorStats              `json:"summary_stats"` // ADDED: Key author metrics
	Topics                  []Topic                  `json:"topics"`        // MODIFIED: Replaced Concepts with the richer Topics struct
	LastFetched             time.Time                `json:"-"`
}

// Institution corresponds to the Institution entity from OpenAlex.
type Institution struct {
	// ... (no changes to this struct) ...
}

// Work corresponds to the Work entity from OpenAlex.
type Work struct {
	ID                          string          `json:"id"`
	Title                       string          `json:"title"`
	Doi                         string          `json:"doi"`
	Type                        string          `json:"type"` // ADDED: Critical context (journal-article, etc.)
	PublicationDate             string          `json:"publication_date"`
	PublicationYear             int             `json:"publication_year"`
	CitedByCount                int             `json:"cited_by_count"`
	IsRetracted                 bool            `json:"is_retracted"`
	ReferencedWorks             []string        `json:"referenced_works"`
	RelatedWorks                []string        `json:"related_works"` // ADDED: Important new relationship
	Locations                   []Location      `json:"locations"`
	PrimaryLocation             *Location       `json:"primary_location"`
	BestOaLocation              *Location       `json:"best_oa_location"`
	Grants                      []Grant         `json:"grants"`                        // ADDED: Links to funding
	SustainableDevelopmentGoals []DehydratedSDG `json:"sustainable_development_goals"` // ADDED: Links to UN Goals
	Topics                      []Topic         `json:"topics"`                        // MODIFIED: Replaced Concepts with the richer Topics struct
	Authorships                 []Authorship    `json:"authorships"`
}

// --- Topic Hierarchy Structs (NEW) ---

// TopicParent is a generic struct for the hierarchical parents of a topic.
type TopicParent struct {
	ID          string `json:"id"`
	DisplayName string `json:"display_name"`
}

// Topic represents a single topic with its full hierarchy and score.
type Topic struct {
	ID          string      `json:"id"`
	DisplayName string      `json:"display_name"`
	Count       int         `json:"count"`
	Score       float32     `json:"score"`
	Subfield    TopicParent `json:"subfield"`
	Field       TopicParent `json:"field"`
	Domain      TopicParent `json:"domain"`
}

// --- Other New Structs for Added Attributes ---

// Grant represents a funding grant associated with a work.
type Grant struct {
	Funder            string `json:"funder"`
	FunderDisplayName string `json:"funder_display_name"`
	AwardID           string `json:"award_id"`
}

// DehydratedSDG represents a UN Sustainable Development Goal.
type DehydratedSDG struct {
	ID          string  `json:"id"`
	DisplayName string  `json:"display_name"`
	Score       float32 `json:"score"`
}

// AuthorStats contains key metrics for an author's impact.
type AuthorStats struct {
	HIndex   int `json:"h_index"`
	I10Index int `json:"i10_index"`
}

// Concept is still needed for the Author's x_concepts field.
type Concept struct {
	ID          string  `json:"id"`
	DisplayName string  `json:"display_name"`
	Level       int     `json:"level"`
	Score       float64 `json:"score"`
}

// --- Dehydrated, Nested, and Helper Structs ---

// DehydratedInstitution represents the summary view of an institution.
type DehydratedInstitution struct {
	ID          string `json:"id"`
	DisplayName string `json:"display_name"`
	Ror         string `json:"ror"`
	CountryCode string `json:"country_code"`
	Type        string `json:"type"`
}

// DehydratedAuthor represents the summary view of an author.
type DehydratedAuthor struct {
	ID          string `json:"id"`
	DisplayName string `json:"display_name"`
	Orcid       string `json:"orcid"`
}

// DehydratedWork represents the summary view of a work.
type DehydratedWork struct {
	ID              string `json:"id"`
	Doi             string `json:"doi"`
	Title           string `json:"title"`
	PublicationYear int    `json:"publication_year"`
	PublicationDate string `json:"publication_date"`
}

// --- Nested Relationship and Helper Structs ---

// Affiliation represents the relationship between an author and an institution.
type Affiliation struct {
	Institution DehydratedInstitution `json:"institution"`
	Years       []int                 `json:"years"`
}

// CountsByYear is a nested struct for author statistics.
type CountsByYear struct {
	Year         int `json:"year"`
	WorksCount   int `json:"works_count"`
	CitedByCount int `json:"cited_by_count"`
}

// Authorship details the connection between an Author and a Work.
type Authorship struct {
	AuthorPosition string                  `json:"author_position"`
	Author         DehydratedAuthor        `json:"author"`
	Institutions   []DehydratedInstitution `json:"institutions"`
}

// Location represents a host or repository where a Work is located.
type Location struct {
	IsOa           bool    `json:"is_oa"`
	LandingPageUrl string  `json:"landing_page_url"`
	PdfUrl         string  `json:"pdf_url"`
	License        string  `json:"license"`
	Source         *Source `json:"source"` // MODIFIED: Changed from interface{} to specific type
}

// Concept represents a dehydrated concept associated with an author or work,
// including its relevance score.

type Source struct {
	ID          string `json:"id"`
	DisplayName string `json:"display_name"`
	Type        string `json:"type"`
}
