package domain

// This file defines the Go structs equivalent to your Java Spring models.
// It correctly handles both full and "dehydrated" entity representations from the OpenAlex API.

// --- Core Entities ---

// Author corresponds to your Author.java entity.
type Author struct {
	ID                      string                 `json:"id"`
	DisplayName             string                 `json:"display_name"`
	DisplayNameAlternatives []string               `json:"display_name_alternatives"`
	Orcid                   string                 `json:"orcid"`
	CitedByCount            int                    `json:"cited_by_count"`
	WorksCount              int                    `json:"works_count"`
	WorksApiUrl             string                 `json:"works_api_url"`
	CreatedDate             string                 `json:"created_date"`
	UpdatedDate             string                 `json:"updated_date"`
	CountsByYear            []CountsByYear         `json:"counts_by_year"`
	LastKnownInstitution    *DehydratedInstitution `json:"last_known_institution"` // CORRECTED
	Affiliations            []Affiliation          `json:"affiliations"`
	Ids                     map[string]string      `json:"ids"`
}

// Institution corresponds to your Institution.java entity.
type Institution struct {
	ID                      string                  `json:"id"`
	Ror                     string                  `json:"ror"`
	DisplayName             string                  `json:"display_name"`
	DisplayNameAcronyms     []string                `json:"display_name_acronyms"`
	DisplayNameAlternatives []string                `json:"display_name_alternatives"`
	Type                    string                  `json:"type"`
	CountryCode             string                  `json:"country_code"`
	HomepageUrl             string                  `json:"homepage_url"`
	ImageUrl                string                  `json:"image_url"`
	ImageThumbnailUrl       string                  `json:"image_thumbnail_url"`
	International           map[string]string       `json:"international"`
	WorksCount              int                     `json:"works_count"`
	CitedByCount            int                     `json:"cited_by_count"` // CORRECTED
	WorksApiUrl             string                  `json:"works_api_url"`
	CreatedDate             string                  `json:"created_date"`
	UpdatedDate             string                  `json:"updated_date"`
	Ids                     map[string]string       `json:"ids"`
	AssociatedInstitutions  []DehydratedInstitution `json:"associated_institutions"` // CORRECTED
}

// Work corresponds to your Work.java entity.
type Work struct {
	ID                        string                  `json:"id"`
	Title                     string                  `json:"title"`
	Doi                       string                  `json:"doi"`
	PublicationDate           string                  `json:"publication_date"`
	PublicationYear           int                     `json:"publication_year"`
	CitedByCount              int                     `json:"cited_by_count"`
	HasFulltext               bool                    `json:"has_fulltext"`
	Language                  string                  `json:"language"`
	License                   string                  `json:"license"`
	IsParatext                bool                    `json:"is_paratext"`
	IsRetracted               bool                    `json:"is_retracted"`
	CreatedDate               string                  `json:"created_date"`
	UpdatedDate               string                  `json:"updated_date"`
	Ids                       map[string]string       `json:"ids"`
	Authorships               []Authorship            `json:"authorships"`
	ReferencedWorks           []string                `json:"referenced_works"`
	RelatedWorks              []string                `json:"related_works"`
	CorrespondingInstitutions []DehydratedInstitution `json:"corresponding_institutions"`
	Locations                 []Location              `json:"locations"`
	PrimaryLocation           *Location               `json:"primary_location"` // Use pointer for optional object
	BestOaLocation            *Location               `json:"best_oa_location"` // Use pointer for optional object, CORRECTED tag
}

// --- Dehydrated (Summary) Entities ---

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
	IsOa           bool   `json:"is_oa"`
	LandingPageUrl string `json:"landing_page_url"`
	PdfUrl         string `json:"pdf_url"`
	License        string `json:"license"`
}
