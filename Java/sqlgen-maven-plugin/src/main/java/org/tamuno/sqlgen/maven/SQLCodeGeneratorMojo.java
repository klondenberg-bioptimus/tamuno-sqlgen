/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package org.tamuno.sqlgen.maven;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugins.annotations.Mojo;
import org.apache.maven.plugin.AbstractMojo;
import org.apache.maven.plugin.MojoExecutionException;
import org.apache.maven.plugin.MojoFailureException;
import org.apache.maven.plugins.annotations.Component;
import org.apache.maven.plugins.annotations.Parameter;
import org.apache.maven.project.MavenProject;
import org.tamuno.sqlgen.SQLCodeGenerator;
import org.tamuno.sqlgen.SQLGenParseException;

@Mojo(name = "sqlgen")
public class SQLCodeGeneratorMojo extends AbstractMojo {

    /**
     * @parameter default-value="${project}"
     */
    @Parameter(defaultValue = "${project}", readonly = true, required = true)
    protected MavenProject project;
    
    /**
     * @parameter "
     */
    @Parameter(required = false)
    protected String baseclass;

    @Override
    public void execute() throws MojoExecutionException, MojoFailureException {

        for (Object srcroot : this.project.getCompileSourceRoots()) {
            getLog().info("Source root: " + srcroot.toString());
        }

        try {
            ArrayList<File> sqlgFiles = new ArrayList<File>();
            ArrayList<String> sqlgPackage = new ArrayList<String>();
            for (Object srcroot : this.project.getCompileSourceRoots()) {
                getLog().info("Source root: " + srcroot.toString());
                generateCodeRecursive(new File(srcroot.toString()), sqlgFiles, sqlgPackage, ".sqlg", new File(srcroot.toString()));

            }
        } catch (IOException e) {
            throw new MojoExecutionException("Could not generate Java source code!", e);
        }
    }

    protected void generateCodeRecursive(File src, List<File> result, List<String> packages, String extension, File basepath) throws IOException, MojoFailureException {
        if (src.isFile() && src.getName().toLowerCase().endsWith(extension)) {
            result.add(src);
            String pack = src.getParentFile().getAbsolutePath().substring(basepath.getAbsolutePath().length()+1).replace('/', '.').replace('\\', '.');
            packages.add(pack);
            getLog().info("Found " + src.getAbsolutePath() + " within "+ src.getParentFile().getAbsolutePath() + " for package " + pack);
            generateJavaCode(src, pack, basepath);
            return;
        }
        if (src.isDirectory()) {
            for (File s : src.listFiles()) {
                generateCodeRecursive(s, result, packages, extension, basepath);
            }
        }
    }

    private void generateJavaCode(File src, String pack, File outPath) throws IOException, MojoFailureException {
        SQLCodeGenerator cgen = new SQLCodeGenerator();

        String name = src.getName().substring(0, src.getName().length() - 5);
        File srcTarget = new File(outPath.getAbsolutePath() + File.separator + pack.replace('.', File.separatorChar) + File.separator + name + ".java");
        getLog().info("Creating " + srcTarget.getPath() + " from " + src.getPath() + " baseclass="+this.baseclass);
        try {
            if (!srcTarget.exists() || (src.lastModified() > srcTarget.lastModified())) {
                srcTarget.getParentFile().mkdirs();
                cgen.generateSQLCode(src, srcTarget, pack, name, this.baseclass, false);
            }

        } catch (SQLGenParseException ex) {
            getLog().error("SQL Code Generator: Parse error in " + src.toString() + ":" + ex.getMessage());
            throw new MojoFailureException("SQL Code Generator: Parse error in " + src.toString() + ":" + ex.getMessage(), ex);
        }

    }

}
