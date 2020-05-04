from collections import defaultdict
from typing import List, Dict, Optional

from src.Allele import Allele
from src.AlleleMPHF import AlleleMPHF
from src.DeduplicatedVariationsDataframe import DeduplicatedVariationsDataframe
from src.PairwiseVariation import PairwiseVariation
from src.PangenomeVariation import PangenomeVariation
from src.PangenomeVariations import PangenomeVariations
from src.Utils import Utils
from src.mummer import ShowSNPsDataframe


class InconsistentPangenomeVariations(Exception):
    pass


class ConsistentPangenomeVariations:
    """
    Represents a list of ConsistentPangenomeVariations (built from PangenomeVariations)
    For the definition of consistent Pangenome Variations, see https://github.com/iqbal-lab/pandora1_paper/issues/144#issue-603283664
    """

    def __init__(self, pangenome_variations: PangenomeVariations):
        self._consistent_pangenome_variations = [
            pangenome_variation \
            for pangenome_variation in pangenome_variations.pangenome_variations \
            if pangenome_variation.is_consistent()
        ]

        # this allele to consistent_pangenome_variations indexing is to speedup some methods
        self._alleles_to_consistent_pangenome_variations = defaultdict(lambda: None)
        for consistent_pangenome_variation in self.consistent_pangenome_variations:
            for allele in consistent_pangenome_variation.alleles:
                self._alleles_to_consistent_pangenome_variations[allele] = consistent_pangenome_variation

    @property
    def consistent_pangenome_variations(self) -> List[PangenomeVariation]:
        return self._consistent_pangenome_variations

    @property
    def alleles_to_consistent_pangenome_variations(self) -> Dict[Allele, Optional[PangenomeVariation]]:
        return self._alleles_to_consistent_pangenome_variations

    def get_consistent_pangenome_variation(self, pairwise_variation: PairwiseVariation) -> Optional[PangenomeVariation]:
        # Note: pangenome_variation_of_allele_1/2 can be None
        pangenome_variation_of_allele_1 = self.alleles_to_consistent_pangenome_variations[pairwise_variation.allele_1]
        pangenome_variation_of_allele_2 = self.alleles_to_consistent_pangenome_variations[pairwise_variation.allele_2]

        both_alleles_have_the_same_pangenome_variation = pangenome_variation_of_allele_1 == pangenome_variation_of_allele_2
        if not both_alleles_have_the_same_pangenome_variation:
            raise InconsistentPangenomeVariations()

        return pangenome_variation_of_allele_1

    def _get_DeduplicatedVariationsDataframe(self, ref: str, query: str, snps_df: ShowSNPsDataframe,
                                             allele_mphf: AlleleMPHF) -> DeduplicatedVariationsDataframe:
        """
        Builds a DeduplicatedVariationsDataframe from a ShowSNPsDataframe with info computed from the ConsistentPangenomeVariations.
        ** WARNING: this also modifies snps_df parameter, we dont want to make a copy**

        Adds the following columns to snps_df:
        ref_genome: str
        query_genome: str
        present_in_a_consistent_pangenome_variation: bool
        pangenome_variation_id: int
        number_of_alleles: int
        ref_allele_id: int
        query_allele_id: int
        number_of_different_allele_sequences: int
        ref_allele_sequence_id: int
        query_allele_sequence_id: int

        :return the DeduplicatedVariationsDataframe
        """
        ref_genome = [ref] * len(snps_df)
        query_genome = [query] * len(snps_df)
        present_in_a_consistent_pangenome_variation = [False] * len(snps_df)
        pangenome_variation_id = [-1] * len(snps_df)
        number_of_alleles = [-1] * len(snps_df)
        ref_allele_id = [-1] * len(snps_df)
        query_allele_id = [-1] * len(snps_df)
        number_of_different_allele_sequences = [-1] * len(snps_df)
        ref_allele_sequence_id = [-1] * len(snps_df)
        query_allele_sequence_id = [-1] * len(snps_df)

        for index, pairwise_variation in enumerate(
                PairwiseVariation.get_PairwiseVariation_from_ShowSNPsDataframe(ref, query, snps_df, allele_mphf)):
            consistent_pangenome_variation = self.get_consistent_pangenome_variation(pairwise_variation)
            is_present = consistent_pangenome_variation is not None
            if is_present:
                present_in_a_consistent_pangenome_variation[index] = True
                pangenome_variation_id[index] = consistent_pangenome_variation.id
                number_of_alleles[index] = consistent_pangenome_variation.get_number_of_alleles()
                ref_allele_id[index] = consistent_pangenome_variation.get_allele_index(
                    pairwise_variation.original_ref_allele)
                query_allele_id[index] = consistent_pangenome_variation.get_allele_index(
                    pairwise_variation.original_query_allele)
                number_of_different_allele_sequences[
                    index] = consistent_pangenome_variation.get_number_of_different_allele_sequences()
                ref_allele_sequence_id[index] = consistent_pangenome_variation.get_allele_sequence_index(
                    pairwise_variation.original_ref_allele)
                query_allele_sequence_id[index] = consistent_pangenome_variation.get_allele_sequence_index(
                    pairwise_variation.original_query_allele)

        deduplicated_snps_df = DeduplicatedVariationsDataframe(snps_df)
        deduplicated_snps_df["ref_genome"] = ref_genome
        deduplicated_snps_df["query_genome"] = query_genome
        deduplicated_snps_df[
            "present_in_a_consistent_pangenome_variation"] = present_in_a_consistent_pangenome_variation
        deduplicated_snps_df["pangenome_variation_id"] = pangenome_variation_id
        deduplicated_snps_df["number_of_alleles"] = number_of_alleles
        deduplicated_snps_df["ref_allele_id"] = ref_allele_id
        deduplicated_snps_df["query_allele_id"] = query_allele_id
        deduplicated_snps_df["number_of_different_allele_sequences"] = number_of_different_allele_sequences
        deduplicated_snps_df["ref_allele_sequence_id"] = ref_allele_sequence_id
        deduplicated_snps_df["query_allele_sequence_id"] = query_allele_sequence_id
        return deduplicated_snps_df

    def build_DeduplicatedVariationsDataframe_from_ShowSNPsDataframe(self, ShowSNPsDataframe_filepath: str,
                                                                     allele_mphf: AlleleMPHF) -> DeduplicatedVariationsDataframe:
        """
        Loads a ShowSNPsDataframe, add all the relevant information about Consistent Pangenome Variations into it,
        builds the DeduplicatedVariationsDataframe, and filter out variations that are not in a Consistent Pangenome Variation
        """
        ref, query = Utils._get_ref_and_query_from_ShowSNPsDataframe_filepath(ShowSNPsDataframe_filepath)
        snps_df = Utils._load_pickled_ShowSNPsDataframe(ShowSNPsDataframe_filepath)
        deduplicated_snps_df = self._get_DeduplicatedVariationsDataframe(ref, query, snps_df, allele_mphf)
        filtered_snps_df = deduplicated_snps_df[
            deduplicated_snps_df.present_in_a_consistent_pangenome_variation == True]
        filtered_snps_df.reset_index(drop=True, inplace=True)
        return DeduplicatedVariationsDataframe(filtered_snps_df)

    def __repr__(self):
        return str(vars(self))
