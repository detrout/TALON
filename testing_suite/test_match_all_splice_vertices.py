import pytest
from talon import talon, init_refs
from .helper_fns import get_db_cursor
@pytest.mark.dbunit

class TestMatchAllVertices(object):

    def test_all_known_locations(self):
        """ Example where the toy transcript database contains matches for all
            vertices.
        """
        conn, cursor = get_db_cursor()
        build = "toy_build"
        database = "scratch/toy.db"
        talon.get_counters(database)
        location_dict = init_refs.make_location_dict(build, cursor)
        run_info = talon.init_run_info(database, build)
        orig_vertex_count = talon.vertex_counter.value()
        strand = "+"
        conn.close()

        chrom = "chr1"
        pos = [1, 100, 500, 600, 900, 1000]
        vertex_IDs, novelty = talon.match_splice_vertices(chrom, pos, 
                                                                  strand,
                                                                  location_dict, 
                                                                  run_info)

        assert vertex_IDs == [2, 3, 4, 5]
        assert talon.vertex_counter.value() == orig_vertex_count

    def test_with_novel_location(self):
        """ Example where the toy transcript database contains a novel position.
        """
        conn, cursor = get_db_cursor()
        build = "toy_build"
        database = "scratch/toy.db"
        talon.get_counters(database)
        location_dict = init_refs.make_location_dict(build, cursor)
        run_info = talon.init_run_info(database, build)
        orig_vertex_count = talon.vertex_counter.value()
        orig_n_locations = len(location_dict["chr1"])
        conn.close()

        chrom = "chr1"
        strand = "+"
        pos = [1, 150, 500, 600, 900, 1000]
        vertex_IDs, novelty = talon.match_splice_vertices(chrom, pos, 
                                                                  strand,
                                                                  location_dict, 
                                                                  run_info)

        # Make sure that no match got returned
        new_vertex_count = talon.vertex_counter.value()
        assert vertex_IDs == [ new_vertex_count, 3, 4, 5]
       
        # Make sure the data structures got updated
        assert new_vertex_count == orig_vertex_count + 1
        assert len(location_dict["chr1"]) == orig_n_locations + 1


