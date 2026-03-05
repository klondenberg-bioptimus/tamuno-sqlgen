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
package org.tamuno.annotations;

import java.lang.annotation.*;

/**
 * Annotation, which signals that the annotated class or type has been generated from
 * another file (given by the from argument as a filename relative to the current source file)
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface Generated { 
    public String from() default "";
}
