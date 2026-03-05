/*

 Tamuno Framework 

Copyright: Kai Londenberg, 2007, Germany.

This software is made available as is, without any explicit
or implied warranties, to the extent permitted by law.

The Tamuno Framework is licensed under the Apache Public License V2.0
see LICENSE.txt

The TamunoFramework contains external Open Source Libraries, to
which the original Author has no copyright, and which are
available under their own licensing terms.

*/

package org.tamuno.ant;

import java.io.IOException;
import org.apache.tools.ant.BuildException;
import org.apache.tools.ant.taskdefs.MatchingTask;
import java.io.File;
import org.apache.tools.ant.DirectoryScanner;
import org.tamuno.sqlgen.SQLCodeGenerator;
import org.tamuno.sqlgen.SQLGenParseException;
import org.tamuno.util.TamunoUtils;

/**
 * Ant Task to generate SQL Code Generator classes
 * 
 * Usage example
 * 
 *     <taskdef name="csql" classname="org.tamuno.ant.TamunoSQLCodeGeneratorTask" classpath="tamuno-lib/tamuno.jar:tamuno-lib/antlr-runtime-3.0.1.jar:tamuno-lib/tools.jar" />
 *   
 *     <target name="tamuno-sql" depends="init">
 *       <csql path="${src.dir}" targetpath="${src.dir}" >
 *            <include name="** /*.sqlg"  />
 *       </csql>
 *   </target>
 * 
 */
public class TamunoSQLCodeGeneratorTask extends MatchingTask {
    private File path;
    private File targetpath;

    /**
     * Root source path to start processing at.
     */
    public void setPath(File path) {
        this.path = path;
    }

   /**
    * Output directory (defaults to source path)
    */
    public void setTargetpath(File targetpath) {
        this.targetpath = targetpath;
    }

    /**
     * Main execute method of this ant Task.
     * executes, after init() has been called, and all properties have been set
     */
    @Override
    public void execute() throws BuildException {
        log("Executing TamunoSQLCodeGeneratorTask");
        DirectoryScanner scanner = this.getDirectoryScanner(path);
        if (targetpath==null) {
            targetpath = path;
        }
        String rfnames[] = scanner.getIncludedFiles();
        File srcfiles[] = new File[rfnames.length];
        File targetfiles[] = new File[rfnames.length];
        String packagenames[] = new String[rfnames.length];
        String classnames[] = new String[rfnames.length];
        String baseclasses[] = new String[rfnames.length];
        for (int i=0;i<rfnames.length;i++) {
                String rf = rfnames[i];
                srcfiles[i] = new File(scanner.getBasedir().getAbsolutePath()+File.separator+rf);
                String fname = srcfiles[i].getName();
                int cpos = fname.lastIndexOf('.');
                if (cpos<0) continue;
                baseclasses[i] = null;
                int dpos = fname.lastIndexOf('.', cpos-1);
                if (dpos<0) {
                    dpos = cpos;
                    baseclasses[i] = null;
                    classnames[i] = fname.substring(0, dpos);
                } else {
                    baseclasses[i] = fname.substring(0, dpos);
                    classnames[i] = baseclasses[i] + TamunoUtils.capitalize(fname.substring(dpos+1, cpos));
                }
                dpos = rf.lastIndexOf('.');
                String relbase = rf.substring(0, dpos);
                dpos = relbase.lastIndexOf(File.separator);
                packagenames[i] = rf.substring(0, dpos).replace(File.separatorChar, '.');
                
        }
        SQLCodeGenerator cgen = new SQLCodeGenerator();
        for (int i=0;i<rfnames.length;i++) {
            try {
                File srcTarget = new File(this.targetpath + File.separator + packagenames[i].replace('.', File.separatorChar) + File.separator + classnames[i] + ".java"); 
                if (baseclasses[i]!=null) {
                        File baseTarget = new File(this.targetpath +File.separator + packagenames[i].replace('.', File.separatorChar) + File.separator + baseclasses[i] + ".java");
                        if (srcfiles[i].exists() || (srcfiles[i].lastModified()>srcTarget.lastModified())) {
                            cgen.generateSQLCode(srcfiles[i], baseTarget, packagenames[i], baseclasses[i], null, true);
                            cgen.generateSQLCode(srcfiles[i], srcTarget, packagenames[i], classnames[i], baseclasses[i], true);
                        }
                } else {
                       if (srcfiles[i].exists() || (srcfiles[i].lastModified()>srcTarget.lastModified())) {
                            cgen.generateSQLCode(srcfiles[i], srcTarget, packagenames[i], classnames[i], null, false); 
                       }
                }
            } catch (SQLGenParseException ex) {
                this.log("Parse error in " +  rfnames[i] + ":" + ex.getMessage());
                throw new BuildException(ex);
            } catch (IOException ex) {
                throw new BuildException(ex);
            }
        }
        
    }

    @Override
    public void init() throws BuildException {
    }

    /**
     * Implementation of TamunoUserInterface
     * displays a warning to the user
     */
    public void displayWarning(String message) {
        this.log(message);
    }

    /**
     * Implementation of TamunoUserInterface
     * displays or logs a helpful trace message.
     */
    public void logTrace(String message) {
        this.log(message);
    }

    /**
     * Implementation of TamunoUserInterface
     * displays or logs an Exception - possibly including Stack Trace.
     */
    public void logException(Throwable t) {
        this.log(t, 0);
    }
    
    
}

