# fusion.py — All 4 keyword detectors + Fusion V9

def detect_attentive_signals(text):
    text_lower = text.lower()
    score = 0.0
    strong = [
        'i understand','i get it now','makes sense now','that makes sense',
        'now i understand','now i see','i follow','understand now','understood',
        'clear now','that is clear','very clear','makes complete sense',
        'i see the connection','i see how','i understand this',
        'understand this concept','understand clearly',
        'interesting','fascinating','amazing','love this topic',
        'enjoy this','enjoying this','want to learn more','want to know more',
        'curious about','really interested','can you explain more',
        'tell me more about','can we explore','can we go deeper',
        'another example please','one more example','practice more',
        'i think the answer is','i believe the answer','my answer is',
        'this is related to','this connects to','similar to what',
        'like what we learned','reminds me of','i noticed a pattern',
        'i see a pattern','noticed an interesting','noticed something',
        'noticed a','interesting pattern','how can we apply','how do we apply',
        'when do we use this','what happens if','can this be applied',
        'real world','real life example','practical application',
        'clarify the','clarify this','clarify that',
        'paying attention','was paying','have a question',
        'got a question','quick question','can we do another',
        'do another example','another example','show one more',
        'can you explain more','explain more about','more about this',
        'can you show','show me','followed every step','followed the steps',
        'following along','followed along','keeping up','kept up',
        'see the connection','see the relationship','connects to what',
        'connects to','connection between','learned before',
        'really interesting','very interesting','quite interesting',
        'so interesting','this is interesting','that is interesting',
    ]
    moderate = [
        'oh i see','ah i see','ah okay i understand',
        'that helps a lot','very helpful',
        'great explanation','good explanation',
        'please','can you','could you',
    ]
    for s in strong:
        if s in text_lower: score += 0.25
    for s in moderate:
        if s in text_lower: score += 0.10
    return min(score, 1.0)


def detect_bored_signals(text):
    text_lower = text.lower()
    score = 0.0
    strong = [
        'boring','bored','so boring','this is boring','so bored',
        'i am bored','im bored','not interested','dont care',"don't care",
        'who cares','whatever','so what','repetitive','so repetitive',
        'already know','i know this','knew this','covered this',
        'we did this','done this before','same thing','same stuff',
        'move on','can we move','skip this','skip ahead','go faster',
        'how much longer','when does this end','want a break',
        'class over','wish class','wish class was over','wish this was over',
        'class was over','end already','not interesting','uninteresting',
        'waste of time','wasting time','ok ok','yeah yeah','sure sure',
        'fine fine','ok fine','fine ok','sure fine','hmm ok','ok sure',
        'yeah sure','ok got it','i guess','i suppose',
        "don't see why we",'dont see why we','see why we need',
        'why we need this','why we need to','why are we doing this',
        'why do we do this',"don't see why",'dont see why',
        'why do we need','why are we learning',
        'not relevant','not useful','never use this',
        'will never use','when will i use','pointless',
    ]
    moderate = [
        'ok','okay','sure','fine','yeah',
        'yep','yup','hmm','uh huh','alright','right','got it',
    ]
    for s in strong:
        if s in text_lower: score += 0.25
    words = text_lower.strip().split()
    if len(words) <= 3: score += 0.20
    for s in moderate:
        if text_lower.strip() == s: score += 0.30
    return min(score, 1.0)


def detect_confusion_signals(text):
    text_lower = text.lower()
    score = 0.0
    strong = [
        'confused','confusing',"don't understand",'dont understand',
        'not understand','no idea','what does','what is','how does',
        'why does','what do you mean','repeat','explain again',
        'start over','which formula',"doesn't make sense",'makes no sense',
        "don't follow",'dont follow','not following','can you repeat',
        'say that again','clarify','nothing is making sense',
        'nothing makes sense','not making sense','making no sense',
        "don't see how",'dont see how','see how these','see how this',
        'go over that','go over this','go back','one more time','once more',
        'not sure','not clear','unclear','which step','which part',
        'lost me','losing me','stumped','drawing a blank','too fast',
        'slow down','hold on','back up','completely lost','totally lost',
        'so lost','getting lost','i am lost','im lost','am lost',
        'feel lost','feeling lost','lost right now',
        'explain that again','explain this again','explain again',
        'explain it again','explain once more','from the beginning',
        'from beginning','from scratch','i thought','thought it was',
        'opposite of','other way','backwards',
        'making sense right now','making any sense','sense right now',
        'explain that differently','explain differently',
        'another way','different way','rephrase',
        'in simpler terms','simpler way','easier way','break it down',
        'what is the difference','difference between',
        'how are these different','how is this different',
        'which equation','which method','which approach',
        'supposed to use','are we supposed','should we use',
        'makes no sense to me','no sense to me','doesnt make sense',
    ]
    moderate = [
        'wait','huh','what','how','why','but','opposite','different',
        'expected','supposed to','should be','instead',
        'again','slower','pause','stop','moment','lost','missed',
    ]
    score += min(text.count('?') * 0.15, 0.3)
    for s in strong:
        if s in text_lower: score += 0.25
    for s in moderate:
        if s in text_lower: score += 0.10
    extra = [
        'explain that','explain this','explain it',
        'differently','in a different','another approach',
    ]
    for s in extra:
        if s in text_lower: score += 0.15
    return min(score, 1.0)


def detect_frustration_signals(text):
    text_lower = text.lower()
    score = 0.0
    strong = [
        'give up',"can't do",'cant do','too hard','impossible',
        'never understand','stupid','failing','failed','frustrated',
        'frustrating','hopeless','hate this','tired of','sick of',
        'done with','quit','terrible','stressed','stress','anxious',
        'overwhelmed','exhausted','burned out','burnt out',
        'no matter what','no matter how','over and over','again and again',
        'same mistake','not working',"won't work",'wont work',
        'cannot do','cannot understand','will never','never get',
        'never learn','too much','too complex','too complicated',
        'feel dumb','feel stupid','so frustrated','so stressed',
        'so hard','so difficult','making me crazy','driving me crazy',
        'want to cry','lost hope','lost confidence','keep failing',
        'every time i try','no matter what i do',
        'keep getting','keeps getting','getting it wrong','getting wrong',
        'wrong answer','wrong again','always wrong','still wrong',
        "don't think i will",'will ever understand','ever understand',
        'never going to','never figure','never able',
        'so complicated','way too difficult','way too hard',
        'way too complex','too difficult for me','too hard for me',
        'beyond me','out of my depth','nothing i do',
        'nothing seems to work','nothing works for me',
        'nothing is working','no matter what i try',
        'everything i try','everything fails','been trying',
        'keep trying','tried everything','tried so hard',
        'trying so hard',"still don't get",'still dont get',
        'still not getting',"still can't understand",
        'still cant understand','still confused',
        'studied but','studied this but','studied and still',
        'seems to work','doesnt work','not working for me',
        'getting nowhere','no progress','making no progress',
    ]
    moderate = [
        'hard','difficult','struggle','wrong','still',
        'always','never','every time','keep getting',
        'stuck','blocked','helpless','constantly','repeatedly','keeps','again',
    ]
    for s in strong:
        if s in text_lower: score += 0.3
    for s in moderate:
        if s in text_lower: score += 0.1
    return min(score, 1.0)


def fuse(vision_result, nlp_result, student_text):
    import numpy as np
    classes = ['Attentive', 'Bored', 'Confused', 'Frustrated']

    vp  = np.array([vision_result['proba'].get(c, 0.0) for c in classes])
    np_ = np.array([nlp_result['proba'].get(c, 0.0) for c in classes])

    vl  = vision_result['label']
    nl  = nlp_result['label']
    vc  = vision_result['confidence']
    nc  = nlp_result['confidence']

    att  = detect_attentive_signals(student_text)
    brd  = detect_bored_signals(student_text)
    conf = detect_confusion_signals(student_text)
    fru  = detect_frustration_signals(student_text)

    signals    = {'Attentive': att, 'Bored': brd, 'Confused': conf, 'Frustrated': fru}
    best_cls   = max(signals, key=signals.get)
    best_score = signals[best_cls]
    score_map  = {'Attentive': 100, 'Bored': 40, 'Confused': 60, 'Frustrated': 20}

    # ✅ Priority 0 — strong text signal overrides everything
    if best_score >= 0.4:
        if not (best_cls == 'Bored' and vl == 'Attentive'):
            if not (best_cls == 'Attentive' and vl == 'Bored' and brd > 0.2):
                confidence = min(0.5 + best_score * 0.5, 0.95)
                att_score  = int(score_map[best_cls] * confidence +
                                 score_map[best_cls] * (1 - confidence) * 0.5)
                return _result(best_cls, att_score, confidence, vl, nl)

    # ✅ Priority 1 — if text provided trust NLP much more
    if student_text.strip():
        if nc > 0.6:
            # NLP is confident and has text — trust it 80%
            fp = 0.2 * vp + 0.8 * np_
        else:
            # NLP less confident — 40/60 split
            fp = 0.4 * vp + 0.6 * np_

    # ✅ Priority 2 — no text, vision only rules
    else:
        if vl == nl:
            fp = 0.5 * vp + 0.5 * np_
        elif vl == 'Attentive':
            fp = 0.7 * vp + 0.3 * np_
        elif vl == 'Bored' and nl in ['Confused', 'Frustrated']:
            fp = 0.2 * vp + 0.8 * np_
        elif vl == 'Bored' and nl == 'Attentive':
            fp = (0.65*vp + 0.35*np_) if vc > nc else (0.35*vp + 0.65*np_)
        else:
            total = vc + nc
            fp    = (vc/total)*vp + (nc/total)*np_

    pid       = int(np.argmax(fp))
    label     = classes[pid]
    confidence= float(fp[pid])
    att_score = int(score_map[label]*confidence + score_map[label]*(1-confidence)*0.5)
    return _result(label, att_score, confidence, vl, nl)


def _result(label, score, confidence, vision_label, nlp_label):
    return {
        'final_label'    : label,
        'attention_score': score,
        'confidence'     : round(confidence * 100, 2),
        'vision_label'   : vision_label,
        'nlp_label'      : nlp_label,
    }