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

import java.util.ArrayList;
import java.util.BitSet;

class SQLGenExpression {
    int startTokenIndex;
    int stopTokenIndex;
    boolean optional;
    boolean alternative = false;
    boolean combiner = false;
    boolean stopCombiner = false;
    ArrayList<SQLGenExpression> subExpressions = new ArrayList<SQLGenExpression>();
    long requiredInputVars = 0L;
   
    SQLGenExpression(int startTokenIndex, boolean optional) {
        this.startTokenIndex = startTokenIndex;
        this.stopTokenIndex = startTokenIndex;
        this.optional = optional;
    }
    
    void setRequiredInputVar(int idx) {
        long mask = 1 << idx;
        requiredInputVars |= mask;
    }
    
    void closeExpression(int stopTokenIndex, ArrayList<SQLGenToken> tokens) {
        this.stopTokenIndex = stopTokenIndex;
        if (optional) {
            if ((requiredInputVars==0L) && (subExpressions.size()>0)) {
                alternative = true;
            } else if ((requiredInputVars==0L) && (subExpressions.size()==0)) {
                if ((this.startTokenIndex+2)>=this.stopTokenIndex) {
                    SQLGenToken t = tokens.get(stopTokenIndex-1);
                    if ((t.type == SQLGenTokenType.LITERAL) && (t.value.length()==0)) {
                        this.stopCombiner = true;
                    }
                }
                combiner = true;
                return;
            }
        }
        for (int i=0;i<subExpressions.size();i++) {
            SQLGenExpression subExpr = subExpressions.get(i);
            if (subExpr.requiredInputVars!=0L){
                if (alternative) {
                    requiredInputVars |= subExpr.requiredInputVars;
                }
                continue;
            }
            // Combiner sub-expression depends on required input vars of following subexpression
            // Plus the combine flag.
            if (subExpr.combiner) {
                if (i<subExpressions.size()-1) {
                    subExpr.requiredInputVars |= subExpressions.get(i+1).requiredInputVars;
                }
            }
            
        }
        
    }

}
