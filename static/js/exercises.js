function checkAnswer(el, isCorrect){

    if(isCorrect){
        el.classList.add("correct");
    }else{
        el.classList.add("wrong");

        setTimeout(()=>{
            el.classList.remove("wrong");
        },500);
    }
}