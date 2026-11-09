package io.aethercraft.visuals;

import io.aethercraft.visuals.ChatQuizEngine.QuizQuestion;
import java.util.List;

/**
 * Catalogue des questions du Sphinx Céleste (Aether Trivia Quiz).
 */
public final class ChatQuizCatalog {

    private ChatQuizCatalog() {}

    public static void populateQuestions(List<QuizQuestion> pool) {
        pool.clear();
        pool.add(new QuizQuestion(
                "Quel minerai rare est indispensable pour fabriquer des lingots de Netherite ?",
                "Débris Antique", "debris antique", "debris", "ancient debris", "debriss"));
        pool.add(new QuizQuestion(
                "Combien d'yeux de l'Ender au maximum faut-il pour activer un portail de l'End ?",
                "12", "12", "douze", "12 yeux"));
        pool.add(new QuizQuestion(
                "Quel outil et matériau minimum sont nécessaires pour récolter de l'obsidienne ?",
                "Pioche en Diamant", "pioche en diamant", "pioche diamant", "pioche en netherite", "pioche netherite", "diamant", "diamond pickaxe"));
        pool.add(new QuizQuestion(
                "Comment s'appelle le boss volant invoqué avec 3 crânes squelettes et 4 blocs de sable des âmes ?",
                "Le Wither", "wither", "le wither", "wither boss"));
        pool.add(new QuizQuestion(
                "Quel ingrédient est nécessaire pour fabriquer une potion de régénération avec une potion étrange ?",
                "Larme de Ghast", "larme de ghast", "larme de spectre", "ghast tear", "larme ghast", "larme"));
        pool.add(new QuizQuestion(
                "Quelle créature sous-marine hostile garde les Temples Océaniques avec un rayon laser ?",
                "Le Gardien", "gardien", "le gardien", "guardian", "grand gardien", "elder guardian"));
        pool.add(new QuizQuestion(
                "Quel bloc permet d'amortir 100% des dégâts de chute en atterrissant dessus ?",
                "Seau d'eau / Bloc de foin", "eau", "seau d eau", "foin", "bloc de foin", "slime", "bloc de slime", "toile", "toile d araignee", "water"));
        pool.add(new QuizQuestion(
                "Quelle créature peut être tondue pour récolter des champignons rouges ou bruns ?",
                "La Champimeuh", "champimeuh", "la champimeuh", "mooshroom", "vache champignon", "champivache"));
        pool.add(new QuizQuestion(
                "Combien de lingots de fer au total faut-il pour fabriquer une enclume complète ?",
                "31", "31", "trente et un", "trente-et-un", "31 lingots"));
        pool.add(new QuizQuestion(
                "Quel enchantement de bottes permet de geler l'eau sous vos pas ?",
                "Semelles Givrantes", "semelles givrantes", "frost walker", "marche givree", "givre"));
        pool.add(new QuizQuestion(
                "Comment s'appelle la dimension céleste flottante qui inspire notre archipel ?",
                "L'Aether", "aether", "l aether", "the aether"));
        pool.add(new QuizQuestion(
                "Quel mob neutre transporte des blocs et se téléporte lorsqu'on le regarde ?",
                "L'Enderman", "enderman", "l enderman"));
        pool.add(new QuizQuestion(
                "Quel arbre aux fleurs roses donne du bois pastel dans son biome montagneux ?",
                "Le Cerisier", "cerisier", "le cerisier", "cherry", "sakura", "arbre cerisier"));
        pool.add(new QuizQuestion(
                "Combien de points de vie (PV) possède l'Ender Dragon à son apparition ?",
                "200", "200", "200 pv", "deux cents", "deux cent"));
        pool.add(new QuizQuestion(
                "Quel aliment permet d'apprivoiser un loup sauvage pour en faire un animal de compagnie ?",
                "Un Os", "os", "un os", "des os", "bone"));
        pool.add(new QuizQuestion(
                "Quel minerai céleste exclusif à AetherCraft alimente les rituels et la bourse de l'Agora ?",
                "Étherium", "etherium", "l etherium", "orbe de sang", "aetherium"));
        pool.add(new QuizQuestion(
                "Combien de niveaux d'expérience minimum requiert le plus puissant enchantement sur une table ?",
                "30", "30", "trente", "lvl 30", "niveau 30"));
        pool.add(new QuizQuestion(
                "Quel totem légendaire évite une mort fatale lorsqu'il est tenu en main ?",
                "Totem d'Immortalité", "totem d immortalite", "totem of undying", "totem", "immortalite"));
        pool.add(new QuizQuestion(
                "Quel enchantement d'outil multiplie le nombre de minerais récoltés ?",
                "Fortune", "fortune", "fortune 3", "fortune iii"));
        pool.add(new QuizQuestion(
                "Combien de blocs d'obsidienne au minimum faut-il pour construire un portail du Nether sans coins ?",
                "10", "10", "dix", "10 blocs"));
    }
}
