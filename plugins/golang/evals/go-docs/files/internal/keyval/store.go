package keyval

type Store struct {
	items map[string]string
}

func NewStore() *Store {
	return &Store{items: make(map[string]string)}
}

func (s *Store) Get(key string) (string, bool) {
	v, ok := s.items[key]
	return v, ok
}
