/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */



package org.tamuno.sqlgen;

//~--- non-JDK imports --------------------------------------------------------

import org.junit.AfterClass;
import org.junit.BeforeClass;
import org.junit.Test;

import static org.junit.Assert.*;

//~--- JDK imports ------------------------------------------------------------

import java.io.File;
import org.tamuno.util.TamunoUtils;

/**
 *
 * @author kai
 */
public class SQLCodeGeneratorTest {
    static String currentPath;
    static String expectedPath;
    static File   outDir;
    static String outPath;
    static String srcPath;

    public SQLCodeGeneratorTest() {}

    @BeforeClass
    public static void setUpClass() throws Exception {
        currentPath = new File(".").getCanonicalPath();
        outPath     = currentPath + "/src/test/java/org/tamuno/sqlgen/test/results/";

        outDir      = new File(outPath);
        outDir.mkdirs();
        // Delete resulting files from last run. These could spoil the correctness of the test.
        File remnants[] = outDir.listFiles();
        for (File remnant : remnants) {
            if (remnant.isFile()) {
                remnant.delete();
            }
        }
        srcPath      = currentPath + "/src/test/java/org/tamuno/sqlgen/test/input/";
        expectedPath = currentPath + "/src/test/java/org/tamuno/sqlgen/test/expected/";
    }

    @AfterClass
    public static void checkResults() throws Exception {
        System.err.println("Comparing contents of test.results directory against contents of test.expected");
        File expdir = new File(expectedPath);
        File contents[] = expdir.listFiles();
        if (contents!=null) {
            for (File expected : contents) {
                File result = new File(outDir, expected.getName());
                System.err.println("Compare Check "+expected.getName()+ " generated VS expected version");
                assertTrue(result.exists());
                assertTrue(TamunoUtils.loadTextFile(result).equals(TamunoUtils.loadTextFile(expected)));

            }
        }
    }
    
    /**
     * Test of generateSQLCode method, of class SQLCodeGenerator.
     */
    @Test
    public void generateSQLCode() throws Exception {
        System.out.println("generateSQLCode");

        File             sourceFile           = null;
        File             targetJavaSourceFile = null;
        String           packagename          = "";
        String           classname            = "";
        String           baseclass            = "";
        SQLCodeGenerator instance             = new SQLCodeGenerator();

        instance.generateSQLCode(new File(srcPath+"SQLCode.sqlg"), new File(outPath+"SQLCode.java.txt"), "org.tamuno.sqlgen.test.results", "SQLCode", null, false);
        //assertTrue(TamunoUtils.loadTextFile(new File(outPath+"SQLCode.java.txt"))!=null);
    }

}


//~ Formatted by Jindent --- http://www.jindent.com
