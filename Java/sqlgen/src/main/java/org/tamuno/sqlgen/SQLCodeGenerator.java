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
package org.tamuno.sqlgen;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Stack;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.tamuno.util.TamunoUtils;
import static org.tamuno.sqlgen.SQLGenTokenType.*;

/**
 * <p>
 * Parser and Source Code Generator, which allows to transform
 * specially crafted SQL Code into Java source code, which in turn 
 * provides type safe interfaces to generate clean SQL and to retrieve
 * result sets of queries.
 * </p>
 * <p>
 * The special SQL Syntax is designed to allow type safety and clean markup of optional text pieces.
 * </p>
 * <p>
 * The syntax is simple. A SQL Generator Source file contains a list of SQL Statement Templates.
 * </p>
 * <p>
 * Each of these looks like the following:
 * </p>
 * <PRE>
 * <b>statementName</b>:=MULTILINE SQL CODE<b>;</b>
 * </PRE>
 * <p>
 * That is, each statement begins with its name, and is terminated by a semicolon followed by a newline. 
 * (The final newline after the semicolon is important, so keep it in mind !)
 * 
 * 
 * </p>
 * For the part named <b>MULTILINE SQL CODE</b> above, there are 
 * <ul>
 * <li>Variables (Identified by a starting @, # or $ sign)</li>
 * <li>Optional pieces (Identified by surrounding angle brackets [optional]</li>
 * </ul>
 * <p>
 * Variables can be either <b>input</b> (# and $) or <b>output</b> (@) variables.
 * </p>
 * <p>
 * Variables are identified by a standard <b>identifier</b> (only alphanumeric chars and underscores),
 * and can have a <b>type</b>, and are generally written as 
 * Starting-character ([#$@]) Identifier ([a-Z_]+) (:type)?
 * </p>
 * Input variables can be either 
 * <ul>
 *  <li>Escaped ($)</li>
 *  <li>Literal (#)</li>
 * </ul>
 * <p>
 * Input variables are required parameters, unless contained in an optional section.
 * </p>
 * <p>
 * Optional sections which contain neither input variables nor other optional sections
 * are omitted if either of the surrounding optional sections would be omitted.
 * </p>
 * <p>
 * Optional sections which do not contain input variables, but do contain other optional
 * sections, are called alternative sections. Their content is omitted, unless
 * <em>at least one</em> of the contained alternative sections is not omitted.</p>
 * 
 * <b>Parsing rules</b>
 * <ul>
 * <li>A Backslash (\) can be used to escape special characters.</li>
 * <li>No parsing is done within String-Literals enclosed by " or '</li>
 * </ul>
 * 
 * <b>LIMITS</b>
 * <p>
 * A maximum of 64 different named input variables are allowed, since 64 bit (long) masks are
 * used for quick masking/unmasking of code sections.
 * 
 * If you have more input variables than that, split the expressions up into multiple parts.
 * </b>
 * 
 * <h4>Examples</h4>
 * <PRE>
 * selectUserLogin:=
 *   SELECT @user_id:int, @user_name:String, @birthdate:Date 
 *       FROM users 
 *       WHERE 
 *           user_name=$user_name AND password_hash=md5($password) 
 *       LIMIT 1;
 *
 * selectUser:=
 *   SELECT @user_id:int, ';' @user_name:String, @birthdate:Date 
 *       FROM users 
 *           [ WHERE 
 *               [user_name=$user_name] [AND] [active=$active:int]
 *           ] 
 *       LIMIT 1;
 * </PRE>
 * 
 * @TODO:
 *  Possible enhancements:
 *  <ul>
 *      <li>Execution Wrappers - that is, the possibility to provider Methods wrapping the execution of these Statements</li>
 *      <li>Access levels - The possibility of making certain SQL Statements public, protected, read, write, admin etc.
 *          This info should be passed to the execution wrappers
 *      </li>
 *  </ul>
 *  
 * @see #main
 */
public class SQLCodeGenerator {
    private String baseclass;
    private boolean withDialects;

    private Stack<SQLGenExpression> stack = new Stack<SQLGenExpression>();
    private ArrayList<SQLGenExpression> allExpressions = new ArrayList<SQLGenExpression>();
    private ArrayList<SQLGenToken> allInputVars = new ArrayList<SQLGenToken>();
    private HashMap<String, Integer> inputVarIndices = new HashMap<String, Integer>();
    private HashSet<String> outputVarNames = new HashSet();
    private ArrayList<SQLGenToken> tokens;
    private SqlGenScanner scanner = new SqlGenScanner();
    private String str;
    private static HashMap<String, String[]> targetTypeMap = new HashMap<String, String[]>();
    private int subresultIdx = 0;
    private StringBuilder executor;
    
    private static Pattern statementPattern = Pattern.compile("^([0-9a-zA-Z_]+):=(.*?);$", Pattern.CASE_INSENSITIVE | Pattern.MULTILINE | Pattern.DOTALL);
    /**
     Main API Entry point for the SQL Code Generator
     creates a Java source code file from a given SQL Code Generator source file.
     
     @param sourceFile SQL Code Generator source file to read from
     @param targetJavaSourceFile  Java source code file to write to. (Will be overwritten !)
     @param packagename Package name the target java file will be declared to be in.
     @param classname Classname of the generated class
     @param baseclass base class name of the generated class.
     @throws org.tamuno.sqlgen.SQLGenParseException 
     @throws java.io.IOException 
     @see org.tamuno.ant.TamunoSQLCodeGeneratorTask
    */
    public void generateSQLCode(File sourceFile, File targetJavaSourceFile, String packagename, String classname, String baseclass, boolean withDialects) throws SQLGenParseException, IOException {
        String source = TamunoUtils.loadTextFile(sourceFile, "UTF-8");
        String result = this.generateSQLCode(sourceFile.getAbsolutePath(), source, packagename, classname, baseclass, withDialects);
        TamunoUtils.saveTextFile(targetJavaSourceFile, result, "UTF-8");
    }
    
    public synchronized String generateSQLCode(String srcFileName, String source, String packagename, String classname, String baseclass, boolean withDialects) throws SQLGenParseException, IOException {
        StringBuilder result = new StringBuilder();
        this.withDialects = withDialects;
        this.baseclass = baseclass;
        result.append("package " + packagename + ";\n");
        result.append("\n");
        result.append("import org.tamuno.runtime.sql.*;\nimport org.tamuno.annotations.Generated;\n\n");
        result.append("import java.sql.Connection;\n");
        result.append("import java.sql.Statement;\n");
        result.append("import java.sql.ResultSet;\n");
        result.append("import java.sql.SQLException;\n");
        result.append("import java.io.Serializable;\n");
        
        result.append("/** SQL Code Generator class\n * generated from " + srcFileName + "\n * please do not edit this file by hand.\n */\n");
        result.append("@Generated( from=\""+srcFileName.replace("\\", "\\\\").replace("\"", "\\\"")+"\")\n");
        if (baseclass==null) {
            result.append("public "+((withDialects) ? "abstract " : "") +"class " + classname + " extends BaseSQLApi { \n\n");
        } else {
            result.append("public class " + classname + " extends " + baseclass + " { \n");
        }
        String cl = baseclass;
        if ((baseclass==null) || (!withDialects)) {
            result.append("protected Executor executor;\n\n");
        } 
        if (cl==null) {
            cl = classname;
        }
        if (baseclass==null) {
            result.append("\tpublic "+classname + "() {\n\t\tsuper();\n\t\tthis.executor = new Executor();\n\t}\n");
        
            result.append("\tpublic "+classname + "(Executor executor) {\n\t\tthis.executor = executor;\n\t}\n");
        } else {
            result.append("\tpublic "+classname + "() {\n\t\tsuper();\n\t}\n");
            result.append("\tpublic "+classname + "("+baseclass+".Executor executor) {\n\t\tsuper(executor);\n\t}\n");
        }
        String linePrefix = "\t";
        executor = new StringBuilder();
        executor.append("public static class Executor extends BaseSQLExecutor {\n\n");
        
        Matcher m = statementPattern.matcher(source);
        while (m.find()) {
            String name = m.group(1);
            String src = m.group(2).trim();
            boolean isSelect = src.regionMatches(true, 0, "SELECT ", 0, 7);
            parseString(src);
            result.append(linePrefix + "// Start of code for " + name + "\n");
            result.append(linePrefix + "/** \n");
            String mlines[] = m.group(0).split("\n");
            for (String l : mlines) {
                result.append(linePrefix + " * " + l + "\n");
            }
            result.append(linePrefix + " */\n");
            result.append(createType(name, true, linePrefix));
            
            result.append("\n");
            result.append(createSimpleFactoryMethod(name,linePrefix));
            result.append(createCompleteFactoryMethod(name,linePrefix));
            
            
            result.append("\n");
            if ((baseclass==null) || (!withDialects)) {
                if (outputVarNames.size() > 0) {
                    result.append(createResultType(name, true, linePrefix));
                    result.append("\n");
                } 
                result.append("\n");
            }
            result.append(linePrefix + "// End of code for " + name + "\n\n");

        }
        executor.append("\n}\n\n");
        if ((baseclass==null) || (!withDialects)) {
            result.append(executor);
        }
        result.append("}\n");
        return result.toString();// TamunoUtils.reIndentJavaBlock(result.toString(), 0, "\t").indentedCode;
    }
    
    public void addExecutionWrappers(String basename, String linePrefix, boolean withQuery) {
        String capname = TamunoUtils.capitalize(basename);
        executor.append("\n\n");
        executor.append(linePrefix + "protected int executeUpdate(Statement st, "+capname+" sql) throws SQLException {\n");
        executor.append(linePrefix + "\treturn executeUpdate(st, (Object) sql);\n");
        executor.append(linePrefix + "}\n\n");
        if (withQuery) {
            executor.append(linePrefix + "protected ResultSet executeQuery(Statement st, "+capname+" sql) throws SQLException{\n");
            executor.append(linePrefix + "\treturn executeQuery(st, (Object) sql);\n");
            executor.append(linePrefix + "}\n\n");
        }
    }
    
    public String createSimpleFactoryMethod(String basename, String linePrefix) {
        StringBuilder t = new StringBuilder();
        String capname = TamunoUtils.capitalize(basename);
        if ((baseclass==null) || (!withDialects)) {
            t.append(linePrefix + "public "+((withDialects) ? " abstract " : "") + capname+" "+basename+"()");
        } else {
            t.append(linePrefix + "public "+baseclass+"."+capname+" "+basename+"()");
        }
        if ((baseclass==null) && (withDialects)) {
            t.append(";\n"); // abstract
        } else {
            t.append(" {\n");
            t.append(linePrefix + "\treturn new " +capname+"();\n");
            t.append(linePrefix + "}\n\n");
        }
        return t.toString();
    }
    
    public String createCompleteFactoryMethod(String basename, String linePrefix) {
        StringBuilder t = new StringBuilder();
        String capname = TamunoUtils.capitalize(basename);
        if ((baseclass==null) || (!withDialects)) {
            t.append(linePrefix + "public "+((withDialects) ? " abstract " : "") +capname+" "+basename+"(");
        } else {
            t.append(linePrefix + "public "+baseclass+"."+capname+" "+basename+"(");
        }
        int pc = 0;
        for (int i = 0; i < allInputVars.size(); i++) {
            SQLGenToken tok = allInputVars.get(i);
            String typeInfo[] = targetTypeMap.get(tok.vartype);
            if (pc++>0) {
                t.append(", ");
            }
            t.append(typeInfo[2] + " " + tok.value + "");
            
        }
        if (pc==0) {
            return "";
        }
        if ((baseclass==null) && (withDialects)) {
            t.append(");\n"); // abstract
        } else {      
            t.append(") {\n");
            t.append(linePrefix + "\t"+capname+" result = new " + capname+"();\n");
            for (int i = 0; i < tokens.size(); i++) {
                SQLGenToken tok = tokens.get(i);
                if ((tok.type != ESCAPED_VAR) && (tok.type != LITERAL_VAR)) {
                    continue;
                }
                String typeInfo[] = targetTypeMap.get(tok.vartype);
                t.append(linePrefix +"\tresult."+tok.value + "=" + tok.value+";\n");
            }
            t.append(linePrefix +"\treturn result;\n");
            t.append(linePrefix + "}\n\n");
        }
        return t.toString();
    }
    
    /**
     * Parses a given String, which contains syntactic elements of our SQL Generator Language.
     * the results of this parse operation are stored in this SqlGenParser Object and can
     * be used to create java source code through the createResultType, createParamType and
     * createSQLGeneratorMethod methods.
     * 
     * See main method for a usage example.
     * 
     * @param str SQL intermixed with elements of the SQL Generator Language.
     * @throws org.tamuno.sqlgen.SQLGenParseException
     * @see #createResultType
     * @see #createParamType
     * @see #createSQLGeneratorMethod
     * @see #main
     */
    public synchronized void parseString(String str) throws SQLGenParseException {
        stack.clear();
        allExpressions.clear();
        allInputVars.clear();
        inputVarIndices.clear();
        outputVarNames.clear();
        this.str = str;
        tokens = scanner.scanString(str);
        SQLGenExpression exp = new SQLGenExpression(0, false);
        stack.push(exp);
        allExpressions.add(exp);
        for (int i = 0; i < tokens.size(); i++) {
            SQLGenToken tok = tokens.get(i);
            switch (tok.type) {
                case LITERAL:
                    continue;
                case OPTION_VAR:
                case ESCAPED_VAR:
                case LITERAL_VAR:
                    Integer idx = inputVarIndices.get(tok.value);
                    if (idx == null) {
                        idx = allInputVars.size();
                        inputVarIndices.put(tok.value, idx);
                        allInputVars.add(tok);

                    } else {
                        SQLGenToken tk = allInputVars.get(idx);
                        if (!tk.vartype.equals(tok.vartype)) {
                            throw new SQLGenParseException(-1, "Input variable " + tok.value + " used with differing types in\n"+str);
                        }
                    }
                    requireInputVar(idx);
                    continue;
                case TARGET_VAR:
                    if (!targetTypeMap.containsKey(tok.vartype)) {
                        throw new SQLGenParseException(-1, "Output variable " + tok.value + " is of unknown type: " + tok.vartype+ " in\n"+str);
                    }
                    if (outputVarNames.contains(tok.value)) {
                        throw new SQLGenParseException(-1, "Output variable " + tok.value + " used more than once in\n"+str);
                    }
                    outputVarNames.add(tok.value);
                    continue;
                case OPEN_BRACKET:
                    exp = new SQLGenExpression(i, true);
                    stack.peek().subExpressions.add(exp);
                    stack.push(exp);
                    allExpressions.add(exp);
                    continue;
                case CLOSE_BRACKET:
                    stack.pop().closeExpression(i, tokens);
                    continue;
                case REQUIRED_OPEN_BRACKET:
                    continue;
                case REQUIRED_CLOSE_BRACKET:
                    exp = new SQLGenExpression(i, false);
                    exp.stopCombiner = true;
                    stack.peek().subExpressions.add(exp);
                    continue;
            }
        }
        stack.peek().closeExpression(tokens.size(), tokens);
        if (this.allInputVars.size() > 64) {
            throw new SQLGenParseException(-1, "More than 64 distinct input variables are not allowed. Found in\n"+str);
        }
    }

    /**
     * Creates java source code for the result of the parsed SQL Query (if applicable)
     * @param basename base class name. Will be used to create the classname for the result type
     *                 which will get the Appendix 'Result'
     * @param isStatic Should the class be declared static ? Yes or no
     * @param linePrefix Indentation of the source code.
     * @return Java source code for the generated class. Usually used as an inner class.
     */
    public synchronized String createResultType(String basename, boolean isStatic, String linePrefix) {
        StringBuilder t = new StringBuilder();
        t.append(linePrefix);
        String capname = TamunoUtils.capitalize(basename);
        t.append("public static class " + capname + "Row implements TypedRow, Cloneable, Serializable {\n");
        for (int i = 0; i < tokens.size(); i++) {
            SQLGenToken tok = tokens.get(i);
            if (tok.type != TARGET_VAR) {
                continue;
            }
            String typeInfo[] = targetTypeMap.get(tok.vartype);
            t.append(linePrefix + "\tpublic " + typeInfo[0] + " " + tok.value + ";\n");
        }
        t.append("\n");
        t.append(linePrefix + "\tpublic void loadResultSetRow(java.sql.ResultSet rs) throws java.sql.SQLException {\n");
        int vidx = 1;
        for (int i = 0; i < tokens.size(); i++) {
            SQLGenToken tok = tokens.get(i);
            if (tok.type != TARGET_VAR) {
                continue;
            }
            String typeInfo[] = targetTypeMap.get(tok.vartype);
            t.append(linePrefix + "\t\t" + tok.value + "=rs." + typeInfo[1] + "(" + (vidx++) + ");\n");
        }
        t.append(linePrefix + "\t}\n\n");
        t.append(linePrefix + "\tpublic Object clone() {\n"+linePrefix + "\t\ttry {\n"+linePrefix+"\t\t\treturn super.clone();\n"+linePrefix+"\t\t} catch (CloneNotSupportedException cns) {\n"+linePrefix+"\t\t\tcns.printStackTrace();\n"+linePrefix+"\t\t\treturn null;\n"+linePrefix+"\t\t}\n"+linePrefix+"\t}\n\n");
        t.append(linePrefix + "}\n");
        return t.toString();
    }

    /**
     * Creates java source code for the parameters of the parsed SQL Query (if applicable)
     * @param basename base class name. Will be used to create the classname for the result type
     *                 which will get the Appendix 'Params'
     * @param isStatic Should the class be declared static ? Yes or no
     * @param linePrefix Indentation of the source code.
     * @return Java source code for the generated class. 
     */
    public synchronized String createType(String basename, boolean isStatic, String linePrefix) {
        StringBuilder t = new StringBuilder();
        t.append(linePrefix);
        t.append("public ");

        String capname = TamunoUtils.capitalize(basename);
        if ((baseclass!=null) && (withDialects)) {
            t.append(" class " + capname + " extends "+baseclass+"."+capname+" implements Cloneable, Serializable {\n");
        } else {
            t.append(" class " + capname + " implements Cloneable, Serializable {\n");
        }
        if ((baseclass==null) || (!withDialects)) {
            for (int i = 0; i < allInputVars.size(); i++) {
                SQLGenToken tok = allInputVars.get(i);
                String typeInfo[] = targetTypeMap.get(tok.vartype);
                if (typeInfo==null) {
                    throw new RuntimeException("Unknown variable type: "+ tok.vartype + " of variable "+tok.value);
                }
                t.append(linePrefix + "\tpublic " + typeInfo[2] + " " + tok.value + " = null;\n");
            }
            t.append("\n");
            t.append(linePrefix + "\tpublic long calcAvailableParamsBitset() {\n");
            t.append(linePrefix + "\t\t" + "long result = 0L;\n");
            long mask = 1;
            for (int i = 0; i < allInputVars.size(); i++) {
                SQLGenToken tok = allInputVars.get(i);
                String typeInfo[] = targetTypeMap.get(tok.vartype);
                t.append(linePrefix + "\t\tif (" + tok.value + "!=null) {\n");
                t.append(linePrefix + "\t\t\tresult |= " + Long.toString(mask) + "L;\n");
                t.append(linePrefix + "\t\t}\n");
                mask <<= 1;
            }
            t.append(linePrefix + "\t\treturn result;\n");

            t.append(linePrefix + "\t}\n\n");

            for (int i = 0; i < allInputVars.size(); i++) {
                SQLGenToken tok = allInputVars.get(i);
                String typeInfo[] = targetTypeMap.get(tok.vartype);
                t.append(linePrefix + "\tpublic "+ capname+" "+tok.value +"("+typeInfo[2] + " value) {\n");
                t.append(linePrefix + "\t\t"+tok.value+" = value;\n");
                t.append(linePrefix + "\t\treturn this;\n"+linePrefix+"\t}\n\n");
            }
            t.append(linePrefix + "\tpublic int execute() throws SQLException {\n");
            t.append(linePrefix +"\t\treturn this.execute(connectionProvider.getConnection().createStatement());\n");
            t.append(linePrefix +"\t}\n\n");

            t.append(linePrefix + "\tpublic int execute(java.sql.Statement st) throws SQLException {\n");
            t.append(linePrefix + "\t\treturn executor.executeUpdate(st, this);\n");
            t.append(linePrefix + "\t}\n\n");
            if (this.outputVarNames.size()>0) {
                t.append(linePrefix + "\tpublic RowIterator<"+capname+"Row> query() throws SQLException {\n");
                t.append(linePrefix +"\t\treturn this.query(connectionProvider.getConnection().createStatement());\n");
                t.append(linePrefix +"\t}\n\n");

                t.append(linePrefix + "\tpublic RowIterator<"+capname+"Row> query(java.sql.Statement st) throws SQLException {\n");
                t.append(linePrefix + "\t\treturn new RowIterator<"+capname+"Row>(executor.executeQuery(st, this), "+capname+ "Row.class);\n");
                t.append(linePrefix + "\t}\n\n");
                this.addExecutionWrappers(capname, linePrefix, true);
            } else {
                this.addExecutionWrappers(capname, linePrefix, false);
            }
        }
        if ((baseclass!=null) || (!withDialects)) {
            t.append(createSQLGeneratorMethod(basename, linePrefix+"\t"));
        }
        t.append("\n");
        
        t.append(linePrefix + "}\n");
        t.append(linePrefix + "\n");
        return t.toString();
    }

    private void requireInputVar(int idx) {
        for (int i = stack.size() - 1; i >= 0; i--) {
            SQLGenExpression e = stack.get(i);
            e.setRequiredInputVar(idx);
            if (e.optional) {
                return;
            }
        }
    }

    /**
     * Generates Java source: A method, which will create a plain SQL String,
     * given type safe arguments in a type which has been generated via createParamType() above.
     * 
     * Executing the given SQL will usually produce a result set which can be parsed by the
     * type generated by createResultType()
     * @param baseName
     * @param isStatic
     * @param linePrefix
     * @return Java source code of the generated method.
     */
    public synchronized String createSQLGeneratorMethod(String baseName, String linePrefix) {
        StringBuilder t = new StringBuilder();
        subresultIdx = 0;
        t.append(linePrefix + "public ");
        if (this.allInputVars.size()>0) {
            t.append(" String toString() {\n");
            t.append(linePrefix + "\t");
            t.append("long available = this.calcAvailableParamsBitset();\n");    
            if (this.allExpressions.get(0).requiredInputVars != 0L) {
                t.append(linePrefix + "\t");
                t.append("if ((available & " + this.allExpressions.get(0).requiredInputVars + "L)!=" + this.allExpressions.get(0).requiredInputVars + "L) {\n");
                t.append(linePrefix + "\t\t");
                t.append("throw new IllegalArgumentException(\"Missing required arguments\");\n");
                t.append(linePrefix + "\t}\n");
            }
        } else {
            t.append(" String toString() {\n");
        }
        t.append(linePrefix + "\t");
        t.append("StringBuilder result = new StringBuilder();\n");
        t.append(linePrefix + "\t");
        t.append("boolean combine = false;\n");
        
        addSQLExpressionGeneratorCode(t, this.allExpressions.get(0), false, linePrefix + "\t", 0, "result", null, "combine");
        t.append(linePrefix + "\treturn result.toString();\n");
        t.append(linePrefix + "}\n");
        return t.toString();
    }

    private void addSQLExpressionGeneratorCode(StringBuilder t, SQLGenExpression expr, boolean checkCondition, String linePrefix, int depth, String resultVar, String altFlag, String combineFlag) {
        String oldLinePrefix = linePrefix;
        String oldResultVar = resultVar;
        String oldAltFlag = altFlag;
        String oldCombineFlag = combineFlag;
        if (expr.stopCombiner) {
            t.append(linePrefix + combineFlag + " = false;\n");
            return;
        }
        if (expr.requiredInputVars==0L) {
            checkCondition = expr.combiner;
        }
        
        if ((!expr.alternative) && (!expr.combiner)) {
            if (checkCondition) {
                t.append(linePrefix + "if ((available & " + expr.requiredInputVars + "L)==" + expr.requiredInputVars + "L) {\n");
                linePrefix = linePrefix + "\t";
            }
            if (altFlag != null) {
                t.append(linePrefix + altFlag + "=true;\n");
            }
        } else if (expr.alternative) {
            if (checkCondition) {
                t.append(linePrefix + "if ((available & " + expr.requiredInputVars + "L)!=0L) {\n");
                linePrefix = linePrefix + "\t";
            }
        } else if (expr.combiner) { 
             if (expr.requiredInputVars==0L) { 
                 t.append(linePrefix + "if ("+oldCombineFlag+") {\n");
             } else {
                 t.append(linePrefix + " if (("+oldCombineFlag+") && ((available & " + expr.requiredInputVars + "L)==" + expr.requiredInputVars + "L)) {\n");               
             }
             linePrefix = linePrefix + "\t";
        }
        if (expr.alternative) {
            subresultIdx++;
            altFlag = "altFlag" + subresultIdx;
            resultVar = "subResult" + subresultIdx;
            combineFlag = "combine" + subresultIdx;
            
            t.append(linePrefix + "StringBuilder " + resultVar + " = new StringBuilder();\n");
            t.append(linePrefix + "boolean " + altFlag + " = false;\n");
            t.append(linePrefix + "boolean "+ combineFlag+" = false;\n");
        }
        int pos = expr.startTokenIndex;
        for (SQLGenExpression nextSubexpression : expr.subExpressions) {
            addPlainCode(t, pos, nextSubexpression.startTokenIndex, linePrefix, resultVar);
            addSQLExpressionGeneratorCode(t, nextSubexpression, true, linePrefix, depth + 1, resultVar, altFlag, combineFlag);
            pos = nextSubexpression.stopTokenIndex + 1;
        }
        addPlainCode(t, pos, expr.stopTokenIndex, linePrefix, resultVar);
        if (!expr.alternative) {
            if (expr.combiner) {
                t.append(linePrefix + oldCombineFlag +" = false;\n");
            } else {
                t.append(linePrefix  + oldCombineFlag +" = true;\n");
            }
            if (checkCondition) {
                t.append(oldLinePrefix + "}\n");
            }
        } else {
            t.append(linePrefix + "if (" + altFlag + ") {\n");
            if (oldAltFlag != null) {
                t.append(linePrefix + "\t" + oldAltFlag + "=true;\n");
            }
            t.append(linePrefix + "\t" + oldResultVar + ".append(" + resultVar + ");\n");
            
            t.append(linePrefix+ "\t"+oldCombineFlag+" = true;\n");
            t.append(linePrefix + "}\n");
            
            if (checkCondition) {
                if (expr.optional) {
                    t.append(oldLinePrefix + "}\n");
                } 
            }
        }
    }

    private void addPlainCode(StringBuilder t, int startToken, int stopToken, String linePrefix, String resultVar) {
        for (int p = startToken; p < stopToken; p++) {
            SQLGenToken tok = tokens.get(p);
            switch (tok.type) {
                case LITERAL:
                case TARGET_VAR:
                    if (tok.value.length() > 0) {
                        t.append(linePrefix + resultVar + ".append(\"" + TamunoUtils.escapeJavaString(tok.value) + "\");\n");
                    }
                    break;
                case LITERAL_VAR:
                    t.append(linePrefix + resultVar + ".append(this." + tok.value + ");\n");
                    break;
                case ESCAPED_VAR:
                    t.append(linePrefix + resultVar + ".append(sqlDialectUtil.escapeValue(this." + tok.value + "));\n");
                    break;
                case OPTION_VAR:
                    // Do nothing .. 
                    break;
            }
            
                //
        }
    }


    /**
     * Usage example for this class.
     * @param args not used.
     */
    public static void main(String args[]) {
        try {
            SQLCodeGenerator parser = new SQLCodeGenerator();
            //parser.parseString("SELECT @a, count(*) as @b:int, @c:Date FROM #table [WHERE [user_id=$user_id:int] [AND] [age>=$min_age:int] [AND] [age BETWEEN $min_age:int AND $max_age]] [LIMIT #limit:int] ");
            //  parser.parseString("SELECT 'Alles klar' @user_id:int, @user_name:String, @birthdate:Date FROM users where [user_name=$user_name][ and ][active=$active:int] LIMIT 1");
              
            /*System.out.println(parser.createResultType("Select", true, "\t"));
            System.out.println(parser.createType("Select", true, "\t"));
             */
            //System.out.println(parser.generateSQLCode("Test.sqlg", "SelectUser:= SELECT @user_id:int, @user_name:String, @birthdate:Date FROM users where [user_name=$user_name][ and ][active=$active:int] LIMIT 1;\n", "test.package", "TestSelectorMyql", null, false));
            System.out.println(parser.generateSQLCode("Test.sqlg", TamunoUtils.loadTextFile(new File("/home/kai/projects/TamunoFramework/tamuno-docs/src/java/org/tamuno/cdocs/data/SQLCode2.MySQL.sqlg"), "UTF-8"),
                        "test.package", "TestSelector", null, false));
        } catch (Exception ex) {
            ex.printStackTrace();
        }
    }
    static {
        targetTypeMap.put("String", new String[]{"String", "getString", "String"});
        targetTypeMap.put("int", new String[]{"int", "getInt", "Integer"});
        targetTypeMap.put("long", new String[]{"long", "getLong", "Long"});
        targetTypeMap.put("double", new String[]{"double", "getDouble", "Double"});
        targetTypeMap.put("float", new String[]{"float", "getFloat", "Float"});
        targetTypeMap.put("short", new String[]{"short", "getShort", "Short"});
        targetTypeMap.put("boolean", new String[]{"boolean", "getBoolean", "Boolean"});
        targetTypeMap.put("byte", new String[]{"byte", "getByte", "Byte"});
        targetTypeMap.put("bytes", new String[]{"byte[]", "getBytes", "byte[]"});
        targetTypeMap.put("decimal", new String[]{"java.math.BigDecimal", "getBigDecimal", "java.math.BigDecimal"});
        targetTypeMap.put("URL", new String[]{"java.net.URL", "getURL", "java.net.URL"});
        targetTypeMap.put("Date", new String[]{"java.sql.Date", "getDate", "java.sql.Date"});
        targetTypeMap.put("Time", new String[]{"java.sql.Time", "getDate", "java.sql.Time"});
        targetTypeMap.put("Timestamp", new String[]{"java.sql.Timestamp", "getTimestamp", "java.sql.Timestamp"});
        targetTypeMap.put("Blob", new String[]{"java.sql.Blob", "getBlob", "String"});
        targetTypeMap.put("Clob", new String[]{"java.sql.Clob", "getClob", "String"});
    }
}
