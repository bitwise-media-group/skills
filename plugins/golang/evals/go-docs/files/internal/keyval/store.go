package keyval

// Store holds parsed key-value pairs.
type Store struct {
	items map[string]string
}

// NewStore returns an empty Store.
func NewStore() *Store {
	return &Store{items: make(map[string]string)}
}

// Get reports the value for key and whether the key exists.
func (s *Store) Get(key string) (string, bool) {
	v, ok := s.items[key]
	return v, ok
}
