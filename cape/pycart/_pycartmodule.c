#include <Python.h>
#include "pc_Tri.h"

// Need this to start NumPy C-API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL _pycart_ARRAY_API
#include <numpy/arrayobject.h>

#include "pc_NumPy.h"

static PyMethodDef Methods[] = {
    // pc_Tri methods
    {"WriteTri", pc_WriteTri, METH_VARARGS, doc_WriteTri},
    {"WriteCompID", pc_WriteCompID, METH_VARARGS, doc_WriteCompID},
    {"WriteTriQ", pc_WriteTriQ, METH_VARARGS, doc_WriteTriQ},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_pycart(void)
{
    // This must be called before using the NumPy API.
    import_array();
    // Initialization command.
    (void) Py_InitModule("_pycart", Methods);
}
