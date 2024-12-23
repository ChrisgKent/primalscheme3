import unittest

from primalscheme3.core.classes import FKmer, PrimerPair, RKmer


class Test_FKmer(unittest.TestCase):
    def test_creation(self):
        seqs = ["ATGC", "ATGCA"]
        seqs.sort()
        end = 100

        # Test case 1: Valid input
        fkmer = FKmer(end, seqs)

        # Test asignments
        self.assertEqual(fkmer.seqs, seqs)
        self.assertEqual(fkmer.end, end)
        self.assertEqual(fkmer.starts(), {end - len(x) for x in seqs})

    def test_len(self):
        seqs = ["ATGC"]
        end = 100

        # Test case 1: Valid input
        fkmer = FKmer(end, seqs)

        # Test asignments
        self.assertEqual(fkmer.len(), [4])

    def test_string_single(self):
        seqs = ["ATGC"]
        end = 100
        reference = "reference"
        amplicon_prefix = "amplicon_prefix"
        pool = "pool"

        # Test case 1: Valid input
        fkmer = FKmer(end, seqs)

        # Test asignments
        self.assertEqual(
            fkmer.__str__(reference, amplicon_prefix, pool),
            "reference\t96\t100\tamplicon_prefix_LEFT_1\tpool\t+\tATGC\n",
        )

    def test_string_multiple(self):
        seqs = ["ATGC", "ATGCA"]
        seqs.sort()

        end = 100
        reference = "reference"
        amplicon_prefix = "amplicon_prefix"
        pool = "pool"

        # Test case 1: Valid input
        fkmer = FKmer(end, seqs)

        # Test asignments
        self.assertEqual(
            fkmer.__str__(reference, amplicon_prefix, pool),
            "reference\t96\t100\tamplicon_prefix_LEFT_1\tpool\t+\tATGC\nreference\t95\t100\tamplicon_prefix_LEFT_2\tpool\t+\tATGCA\n",
        )


class Test_RKmer(unittest.TestCase):
    def test_create(self):
        seqs = ["ATGC"]
        start = 100

        # Test case 1: Valid input
        rkmer = RKmer(start, seqs)

        # Test asignments
        self.assertEqual(rkmer.seqs, seqs)
        self.assertEqual(rkmer.start, start)
        self.assertEqual(rkmer.ends(), {start + len(x) for x in seqs})

    def test_len(self):
        seqs = ["ATGC"]
        start = 100

        # Test case 1: Valid input
        rkmer = RKmer(start, seqs)

        # Test asignments
        self.assertEqual(rkmer.len(), [4])

    def test_ends(self):
        seqs = ["ATGC", "ATGCAA"]
        start = 100

        # Test case 1: Valid input
        rkmer = RKmer(start, seqs)

        # Test asignments
        self.assertEqual(rkmer.ends(), {start + len(x) for x in seqs})

    def test_string_single(self):
        seqs = ["ATGC"]
        start = 100
        reference = "reference"
        amplicon_prefix = "amplicon_prefix"
        pool = "pool"

        # Test case 1: Valid input
        rkmer = RKmer(start, seqs)

        # Test asignments
        self.assertEqual(
            rkmer.__str__(reference, amplicon_prefix, pool),
            "reference\t100\t104\tamplicon_prefix_RIGHT_1\tpool\t-\tATGC\n",
        )

    def test_string_multiple(self):
        seqs = ["ATGC", "ATGCA"]
        seqs.sort()
        start = 100
        reference = "reference"
        amplicon_prefix = "amplicon_prefix"
        pool = "pool"

        # Test case 1: Valid input
        rkmer = RKmer(start, seqs)

        # Test asignments
        self.assertEqual(
            rkmer.__str__(reference, amplicon_prefix, pool),
            "reference\t100\t104\tamplicon_prefix_RIGHT_1\tpool\t-\tATGC\nreference\t100\t105\tamplicon_prefix_RIGHT_2\tpool\t-\tATGCA\n",
        )


class Test_PrimerPair(unittest.TestCase):
    def test_create(self):
        fkmer = FKmer(100, ["ATGC"])
        rkmer = RKmer(1000, ["ATGC"])
        msa_index = 0

        # Test case 1: Valid input
        primerpair = PrimerPair(fprimer=fkmer, rprimer=rkmer, msa_index=msa_index)

        # Test asignments
        self.assertEqual(primerpair.fprimer, fkmer)
        self.assertEqual(primerpair.rprimer, rkmer)
        self.assertEqual(primerpair.msa_index, msa_index)

    def test_set_amplicon_number(self):
        fkmer = FKmer(100, ["ATGC"])
        rkmer = RKmer(1000, ["ATGC"])
        msa_index = 0

        # Test case 1: Valid input
        primerpair = PrimerPair(fprimer=fkmer, rprimer=rkmer, msa_index=msa_index)
        primerpair.set_amplicon_number(1)

        # Test asignments
        self.assertEqual(primerpair.amplicon_number, 1)

    def test_all_seqs(self):
        fkmer = FKmer(100, ["ACTAGCTAGCTAGCA"])
        rkmer = RKmer(1000, ["ATCGATCGGTAC"])
        msa_index = 0

        # Test case 1: Valid input
        primerpair = PrimerPair(fprimer=fkmer, rprimer=rkmer, msa_index=msa_index)

        # Test asignments
        self.assertEqual(primerpair.all_seqs(), ["ACTAGCTAGCTAGCA", "ATCGATCGGTAC"])

    def test_to_bed(self):
        fkmer = FKmer(100, ["ACTAGCTAGCTAGCA"])
        rkmer = RKmer(1000, ["ATCGATCGGTAC"])
        msa_index = 0

        # Test case 1: Valid input
        primerpair = PrimerPair(fprimer=fkmer, rprimer=rkmer, msa_index=msa_index)
        primerpair.pool = 0
        primerpair.set_amplicon_number(0)

        # Test asignments
        expected_pool = primerpair.pool + 1
        expected_refname = "reference"
        expected_amplicon_prefix = "amplicon"

        primerpair.chrom_name = expected_refname
        primerpair.amplicon_prefix = expected_amplicon_prefix

        expected_str = f"{expected_refname}\t85\t100\t{expected_amplicon_prefix}_0_LEFT_1\t{expected_pool}\t+\tACTAGCTAGCTAGCA\n{expected_refname}\t1000\t1012\t{expected_amplicon_prefix}_0_RIGHT_1\t{expected_pool}\t-\tATCGATCGGTAC\n"

        self.assertEqual(primerpair.to_bed(), expected_str)


if __name__ == "__main__":
    unittest.main()
